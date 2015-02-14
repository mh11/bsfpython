"""bsf.analyses.picard

A package of classes and methods modelling Picard analyses data files and data directories.
"""

#
# Copyright 2013 Michael K. Schuster
#
# Biomedical Sequencing Facility (BSF), part of the genomics core facility
# of the Research Center for Molecular Medicine (CeMM) of the
# Austrian Academy of Sciences and the Medical University of Vienna (MUW).
#
#
# This file is part of BSF Python.
#
# BSF Python is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BSF Python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with BSF Python.  If not, see <http://www.gnu.org/licenses/>.


import csv
import errno
import os.path
import re
import string
import warnings

from bsf import Analysis, Command, Configuration, Default, DRMS, Executable, Runnable
from bsf.annotation import LibraryAnnotationSheet
from bsf.data import PairedReads, Sample
from bsf.illumina import RunFolder


def _process_row_dict(barcode_dict, row_dict, prefix=None):
    """Private function to read fields from a Python row_dict object, index by the 'lane' field in the barcode_dict.

    @param barcode_dict: A Python dict of 'lane' key data and Python list objects of lane_dict value data
    @type barcode_dict: dict
    @param row_dict: Python row_dict object
    @type row_dict: dict
    @param prefix: Optional prefix
        (e.g. '[Control] lane', ...)
    @type prefix: str
    @return: Nothing
    @rtype: None
    """

    sample_dict = dict()

    if not prefix:
        prefix = str()

    # Mandatory key 'lane'.
    key1 = str(prefix + ' lane').lstrip(' ')
    sample_dict['lane'] = row_dict[key1]

    # Mandatory key 'barcode_sequence_1'.
    key1 = str(prefix + ' barcode_sequence_1').lstrip(' ')
    sample_dict['barcode_sequence_1'] = row_dict[key1]

    # Optional key 'barcode_sequence_2'.
    key1 = str(prefix + ' barcode_sequence_2').lstrip(' ')
    if key1 in row_dict and row_dict[key1]:
        sample_dict['barcode_sequence_2'] = row_dict[key1]
    else:
        sample_dict['barcode_sequence_2'] = str()

    # Mandatory key 'library_name'.
    key1 = str(prefix + ' library_name').lstrip(' ')
    sample_dict['library_name'] = row_dict[key1]

    # Mandatory key 'sample_name'.
    key1 = str(prefix + ' sample_name').lstrip(' ')
    sample_dict['sample_name'] = row_dict[key1]

    if sample_dict['lane'] in barcode_dict:
        lane_list = barcode_dict[sample_dict['lane']]
        assert isinstance(lane_list, list)
    else:
        lane_list = list()
        barcode_dict[sample_dict['lane']] = lane_list

    lane_list.append(sample_dict)


def extract_illumina_barcodes(config_path):
    """Convert an Illumina Run Folder into BAM files.

    @param config_path: Configuration file
    @type config_path: str | unicode
    @return: Nothing
    @rtype: None
    """

    default = Default.get_global_default()

    analysis = Analysis.from_config_file_path(config_path=config_path)

    cp = analysis.configuration.config_parser
    section = string.join(words=(__name__, analysis.__name__), sep='.')

    if cp.has_option(section=section, option='max_mismatches'):
        max_mismatches = cp.get(section=section, option='max_mismatches')
    else:
        max_mismatches = str()

    if cp.has_option(section=section, option='min_base_quality'):
        min_base_quality = cp.get(section=section, option='min_base_quality')
    else:
        min_base_quality = str()

    # Get the Illumina Run Folder

    illumina_run_folder = cp.get(section=section, option='illumina_run_folder')
    illumina_run_folder = os.path.expanduser(path=illumina_run_folder)
    illumina_run_folder = os.path.expandvars(path=illumina_run_folder)
    if not os.path.isabs(illumina_run_folder):
        os.path.join(Default.absolute_runs_illumina(), illumina_run_folder)

    irf = RunFolder.from_file_path(file_path=illumina_run_folder)

    base_calls_directory = irf.get_base_calls_directory

    # Read the barcodes file ...

    barcode_path = cp.get(section=section, option='barcode_file')
    barcode_path = os.path.expanduser(barcode_path)
    barcode_path = os.path.expandvars(barcode_path)
    # TODO: Prepend path defaults.

    barcode_dict = dict()

    library_annotation_sheet = LibraryAnnotationSheet.from_file_path(file_path=barcode_path)

    for row_dict in library_annotation_sheet.row_dicts:
        assert isinstance(row_dict, dict)
        _process_row_dict(row_dict=row_dict, prefix=analysis.sas_prefix, barcode_dict=barcode_dict)

    # Picard ExtractIlluminaBarcodes

    eib_drms = DRMS.from_analysis(
        name='ExtractIlluminaBarcodes',
        work_directory=analysis.genome_directory,
        analysis=analysis)

    analysis.drms_list.append(eib_drms)

    # Picard IlluminaBasecallsToSam

    ibs_drms = DRMS.from_analysis(
        name='IlluminaBasecallsToSam',
        work_directory=analysis.genome_directory,
        analysis=analysis)

    analysis.drms_list.append(ibs_drms)

    # For each lane in the barcode_dict ...

    keys = barcode_dict.keys()
    keys.sort(cmp=lambda x, y: cmp(x, y))

    for key in keys:
        assert isinstance(key, str)

        # Make a directory L001 - L008 for each lane.
        # TODO: Check if lane is numeric or a string.

        lane_path = os.path.join(analysis.project_directory, 'L{:03d}'.format(int(key)))

        try:
            os.makedirs(lane_path)
        except OSError as exc:  # Python > 2.5
            if exc.errno == errno.EEXIST and os.path.isdir(lane_path):
                pass
            else:
                raise

        barcodes_path = os.path.join(lane_path, '{}_L{:03d}_input_barcodes.txt'.format(irf.flow_cell, int(key)))
        metrics_path = os.path.join(lane_path, '{}_L{:03d}_output_metrics.txt'.format(irf.flow_cell, int(key)))
        library_path = os.path.join(lane_path, '{}_L{:03d}_library.txt'.format(irf.flow_cell, int(key)))

        lane_list = barcode_dict[key]
        assert isinstance(lane_list, list)

        # Check whether all barcodes are of the same length in a particular lane.

        # TODO: Generalise this to any number of barcodes.
        bc1_length = 0
        bc2_length = 9

        for lane_dict in lane_list:
            assert isinstance(lane_dict, dict)

            if lane_dict['barcode_sequence_1'] == 'NoIndex' or not lane_dict['barcode_sequence_1']:
                bc_length = -1
            else:
                bc_length = len(lane_dict['barcode_sequence_1'])

            if not bc1_length:
                bc1_length = bc_length
            else:
                if bc1_length != bc_length:
                    # Barcode lengths do not match ...
                    warnings.warn(
                        'The length {} of barcode 1 {!r} does not match the length ({}) of other barcodes.'.
                        format(bc_length, lane_dict['barcode_sequence_1'], bc1_length),
                        UserWarning)

            if lane_dict['barcode_sequence_2'] == 'NoIndex' or not lane_dict['barcode_sequence_2']:
                bc_length = -1
            else:
                bc_length = len(lane_dict['barcode_sequence_2'])

            if not bc2_length:
                bc2_length = bc_length
            else:
                if bc2_length != bc_length:
                    # Barcode lengths do not match ...
                    warnings.warn(
                        'The length {} of barcode 2 {!r} does not match the length ({}) of other barcodes.'.
                        format(bc_length, lane_dict['barcode_sequence_2'], bc2_length),
                        UserWarning)

        # TODO: Get the read structure from the IRF and the bc_lengths above ...

        for iread in irf.run_information.reads:
            if iread.number == 1:
                if iread.cycles != bc1_length:
                    # TODO: Finish this!
                    warnings.warn()

        # Create a BARCODE_FILE file for Picard ExtractIlluminaBarcodes.
        field_names = ['barcode_sequence_1', 'barcode_sequence_2', 'barcode_name', 'library_name']
        barcodes_file = open(barcodes_path, 'w')
        csv_writer = csv.DictWriter(f=barcodes_file, fieldnames=field_names, dialect=csv.excel_tab)
        csv_writer.writeheader()
        for lane_dict in lane_list:
            # Create a new row dict to adjust column names to the ones required by ExtractIlluminaBarcodes.
            row_dict = dict()
            row_dict['barcode_sequence_1'] = lane_dict['barcode_sequence_1']
            row_dict['barcode_sequence_2'] = lane_dict['barcode_sequence_2']
            row_dict['barcode_name'] = lane_dict['sample_name']
            row_dict['library_name'] = lane_dict['library_name']
            csv_writer.writerow(rowdict=row_dict)
        barcodes_file.close()

        # Create a LIBRARY_PARAMS file for Picard IlluminaBasecallsToSam.
        field_names = ['OUTPUT', 'SAMPLE_ALIAS', 'LIBRARY_NAME', 'BARCODE_1', 'BARCODE_2']
        library_file = open(library_path, 'w')
        csv_writer = csv.DictWriter(f=library_file, fieldnames=field_names, dialect=csv.excel_tab)
        csv_writer.writeheader()
        for lane_dict in lane_list:
            # Create a new row_dict to adjust column names to the ones required by IlluminaBasecallsToSam.
            row_dict = dict()
            row_dict['OUTPUT'] = '{}_{}_L{:03d}_unmapped.bam'.format(lane_dict['sample_name'], irf.flow_cell, int(key))
            row_dict['SAMPLE_ALIAS'] = lane_dict['sample_name']
            row_dict['LIBRARY_NAME'] = lane_dict['library_name']
            row_dict['BARCODE_1'] = lane_dict['barcode_sequence_1']
            row_dict['BARCODE_2'] = lane_dict['barcode_sequence_2']
            csv_writer.writerow(rowdict=row_dict)
        library_file.close()

        # Picard ExtractIlluminaBarcodes

        eib = Executable.from_analysis(name='eib', program='java', analysis=analysis)

        eib_drms.add_executable(eib)

        # Set Java options for Picard ExtractIlluminaBarcodes.

        eib.add_switch_short(key='Xmx6G')  # TODO: Make this configurable somewhere ...

        if default.classpath_picard:
            eib.add_option_short(key='cp', value=default.classpath_picard)

        eib.add_option_short(key='jar', value='ExtractIlluminaBarcodes.jar')

        # These Picard 'options' can be just arguments ...

        eib.arguments.append('BASECALLS_DIR={}'.format(base_calls_directory))
        # OUTPUT_DIR for s_l_t_barcode.txt files not set. Defaults to BASECALLS_DIR.
        eib.arguments.append('LANE={}'.format(int(key)))
        eib.arguments.append('READ_STRUCTURE={}'.format())  # TODO: This would also require barcode lengths.
        # BARCODE not set, since BARCODE_FILE gets used.
        eib.arguments.append('BARCODE_FILE={}'.format(barcodes_path))
        eib.arguments.append('METRICS_FILE={}'.format(metrics_path))
        if max_mismatches:
            eib.arguments.append('MAX_MISMATCHES={}').format()
            # MIN_MISMATCH_DELTA
        # MAX_NO_CALLS
        if min_base_quality:
            eib.arguments.append('MINIMUM_BASE_QUALITY={}'.format(min_base_quality))
            # MINIMUM_QUALITY
        # COMPRESS_OUTPUTS for s_l_t_barcode.txt files
        eib.arguments.append('NUM_PROCESSORS={}'.format(int(eib_drms.threads)))
        eib.arguments.append('COMPRESS_OUTPUTS=TRUE')

        # Picard IlluminaBasecallsToSam

        ibs = Executable.from_analysis(name='ibs', program='java', analysis=analysis)

        ibs_drms.add_executable(ibs)

        # Set Java options for Picard IlluminaBasecallsToSam.

        ibs.add_switch_short(key='Xmx6G')  # TODO: Make this configurable somewhere ...

        if default.classpath_picard:
            ibs.add_option_short(key='cp', value=default.classpath_picard)

        ibs.add_option_short(key='jar', value='IlluminaBasecallsToSam.jar')

        # These Picard 'options' can be just arguments ...

        ibs.arguments.append('BASECALLS_DIR={}'.format(base_calls_directory))
        ibs.arguments.append('LANE={}'.format(int(key)))
        ibs.arguments.append('RUN_BARCODE={}'.format())  # TODO:
        ibs.arguments.append('READ_GROUP_ID={}'.format())  # TODO:
        ibs.arguments.append('SEQUENCING_CENTER={}'.format())  # TODO: Get from Defaults?
        ibs.arguments.append('RUN_START_DATE={}'.format())  # TODO:
        ibs.arguments.append('PLATFORM={}'.format())  # TODO: Defaults to illumina
        ibs.arguments.append('READ_STRUCTURE={}'.format())  # TODO
        ibs.arguments.append('LIBRARY_PARAMS={}'.format(library_path))
        ibs.arguments.append('ADAPTERS_TO_CHECK={}'.format())  # TODO
        ibs.arguments.append('NUM_PROCESSORS={}'.format(int(ibs_drms.threads)))


def picard_sam_to_fastq(analysis):
    """Convert a [BS]AM file into FASTQ format.

    @param analysis: BSF Analysis
    @type analysis: Analysis
    @return: Nothing
    @rtype: None
    """

    assert isinstance(analysis, Analysis)

    default = Default.get_global_default()

    # Always check each BSF PairedReads object separately.
    replicate_grouping = False

    raw_data_directory = os.path.join(analysis.project_directory, 'raw_data')

    if not os.path.isdir(raw_data_directory):

        # In principle, a race condition could occur as the directory
        # could have been created after its existence has been checked.
        try:
            os.makedirs(raw_data_directory)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    # Picard SamToFastq

    stf_drms = DRMS.from_analysis(name='sam_to_fastq',
                                  work_directory=raw_data_directory,
                                  analysis=analysis)

    analysis.drms_list.append(stf_drms)

    # GNU Gzip

    gzip_drms = DRMS.from_analysis(name='gzip',
                                   work_directory=raw_data_directory,
                                   analysis=analysis)

    analysis.drms_list.append(gzip_drms)

    for sample in analysis.samples:
        assert isinstance(sample, Sample)

        if analysis.debug > 0:
            print '{!r} Sample name: {}'.format(analysis, sample.name)
            print sample.trace(1)

        # bsf.data.Sample.get_all_paired_reads returns a Python dict of
        # Python str key and Python list of Python list objects
        # of bsf.data.PairedReads objects.

        replicate_dict = sample.get_all_paired_reads(replicate_grouping=replicate_grouping)

        replicate_keys = replicate_dict.keys()
        replicate_keys.sort(cmp=lambda x, y: cmp(x, y))

        for replicate_key in replicate_keys:
            assert isinstance(replicate_key, str)

            for paired_reads in replicate_dict[replicate_key]:
                assert isinstance(paired_reads, PairedReads)

                if analysis.debug > 0:
                    print '{!r} PairedReads name: {}'.format(analysis, paired_reads.get_name())

                # BAM files should only be set as reads1 in a BSF PairedReads object.

                file_path = str(paired_reads.reads1.file_path)
                file_name = os.path.basename(file_path.rstrip('/ '))
                directory_name = os.path.dirname(file_path.rstrip('/ '))

                # TODO: Let the user specify the file name via a sample annotation sheet or,
                # if not available, match '.unmapped.bam' or just '.bam' and replace by
                # _R1_001.fastq and _R2_002.fastq. Then run GNU Gzip over these files.
                match = re.search(pattern=r'(.*)(?:[._]unmapped)?\.bam$', string=file_name)
                if match:
                    file_path_1 = os.path.join(directory_name, '{}_R1_001.fastq'.format(match.group(1)))
                    file_path_2 = os.path.join(directory_name, '{}_R2_001.fastq'.format(match.group(1)))
                else:
                    warning = "Could not match BAM file name {}".format(file_name)
                    warnings.warn(warning, UserWarning)
                    continue

                # TODO: At this stage, test, whether the files have already been generated.
                # Bail out, if this was the case.

                # TODO: How could the FASTQ files be moved back into the collection?
                # The paired_reads object in this scope would have to get Reads1 replaced and Reads2 added ...

                # TODO: The solution could be to return a richer SampleAnnotationSheet object that points to the
                # new data files and also contains a DRMS job dependency to wait for.

                # TODO: How could the job dependency be communicated back to the analysis?
                # Maybe there should be a Collection method to do the conversion in the context of an analysis?

                stf = Executable(name='sam_to_fastq_{}'.format(replicate_key), program='java')

                stf_drms.add_executable(stf)

                # Set Picard SamToFastq options.

                stf.add_switch_short(key='Xmx4G')
                if default.classpath_picard:
                    stf.add_option_short(key='cp', value=default.classpath_picard)
                stf.add_option_short(key='jar', value='SamToFastq.jar')

                stf.arguments.append('INPUT={}'.format(paired_reads.reads1.file_path))
                stf.arguments.append('FASTQ={}'.format(file_path_1))
                stf.arguments.append('SECOND_END_FASTQ={}'.format(file_path_2))

                gzip = Executable(name='gzip_{}'.format(replicate_key), program='gzip')

                gzip_drms.add_executable(gzip)

                # Set GNU Gzip options

                gzip.add_switch_long(key='best')
                gzip.arguments.append('{}'.format(file_path_1))
                gzip.arguments.append('{}'.format(file_path_2))
                gzip.dependencies.append('{}'.format(stf.name))

                # OUTPUT_PER_RG
                #   Split by ReadGroup would be good, but the file name would be somewhat unpredictable.
                #   We set the read group to FCID.lane
                # OUTPUT_DIR
                # RE_REVERSE
                #   Could be useful to have this configurable.
                # INTERLEAVE
                # INCLUDE_NON_PF_READS
                #   Could be useful to have this configurable.
                # CLIPPING_ATTRIBUTE
                # CLIPPING_ACTION
                # READ1_TRIM
                # READ1_MAX_BASES_TO_WRITE
                # READ2_TRIM
                # READ2_MAX_BASES_TO_WRITE
                # INCLUDE_NON_PRIMARY_ALIGNMENTS

                # TODO: Try a new strategy to pass in a complete Analysis object to allow simpler chaining of analyses.
                # TODO: Maybe this could be used to pass in an ChIPSeq or Tuxedo Analysis object...
                # TODO: The problem is that a BSF Collection may contain more BSF Project and BSF Sample objects
                # than strictly required for the Analysis in question.
                # TODO: We could use a standard directory for data conversion and check if files are already there.
                # A raw_data folder under the analysis.project_directory could work.


class SamToFastq(Analysis):

    @classmethod
    def from_config_file_path(cls, config_path):
        """Create a new C{SamToFastq} object from a UNIX-style configuration file via the C{Configuration} class.

        @param config_path: UNIX-style configuration file
        @type config_path: str | unicode
        @return: C{SamToFastq}
        @rtype: SamToFastq
        """

        return cls.from_configuration(configuration=Configuration.from_config_path(config_path=config_path))

    @classmethod
    def from_configuration(cls, configuration):
        """Create a new C{SamToFastq} object from a C{Configuration} object.

        @param configuration: C{Configuration}
        @type configuration: Configuration
        @return: C{SamToFastq}
        @rtype: SamToFastq
        """

        assert isinstance(configuration, Configuration)

        itb = cls(configuration=configuration)

        # A "bsf.analyses.picard.SamToFastq" section specifies defaults
        # for this Analysis sub-class.

        section = string.join(words=(__name__, cls.__name__), sep='.')
        itb.set_configuration(itb.configuration, section=section)

        return itb

    def __init__(self, configuration=None, project_name=None, genome_version=None, input_directory=None,
                 output_directory=None, project_directory=None, genome_directory=None, e_mail=None, debug=0,
                 drms_list=None, collection=None, comparisons=None, samples=None, classpath_picard=None,
                 include_non_pf_reads=False):
        """Initialise a C{SamToFastq} object.

        @param configuration: C{Configuration}
        @type configuration: Configuration
        @param project_name: Project name
        @type project_name: str
        @param genome_version: Genome version
        @type genome_version: str
        @param input_directory: C{Analysis}-wide input directory
        @type input_directory: str
        @param output_directory: C{Analysis}-wide output directory
        @type output_directory: str
        @param project_directory: C{Analysis}-wide project directory,
            normally under the C{Analysis}-wide output directory
        @type project_directory: str
        @param genome_directory: C{Analysis}-wide genome directory,
            normally under the C{Analysis}-wide project directory
        @type genome_directory: str
        @param e_mail: e-Mail address for a UCSC Genome Browser Track Hub
        @type e_mail: str
        @param debug: Integer debugging level
        @type debug: int
        @param drms_list: Python C{list} of C{DRMS} objects
        @type drms_list: list
        @param collection: C{Collection}
        @type collection: Collection
        @param comparisons: Python C{dict} of Python C{tuple} objects of C{Sample} objects
        @type comparisons: dict
        @param samples: Python C{list} of C{Sample} objects
        @type samples: list
        @param classpath_picard: Picard tools Java Archive (JAR) class path directory
        @type classpath_picard: str | unicode
        @param include_non_pf_reads: Include non-pass filer reads
        @type include_non_pf_reads: bool
        """

        super(SamToFastq, self).__init__(
            configuration=configuration,
            project_name=project_name,
            genome_version=genome_version,
            input_directory=input_directory,
            output_directory=output_directory,
            project_directory=project_directory,
            genome_directory=genome_directory,
            e_mail=e_mail,
            debug=debug,
            drms_list=drms_list,
            collection=collection,
            comparisons=comparisons,
            samples=samples)

        if classpath_picard:
            self.classpath_picard = classpath_picard
        else:
            self.classpath_picard = str()

        self.include_non_pass_filter_reads = include_non_pf_reads

    def set_configuration(self, configuration, section):
        """Set instance variables of a C{SamToFastq} object via a section of a C{Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: C{Configuration}
        @type configuration: Configuration
        @param section: Configuration file section
        @type section: str
        """

        super(SamToFastq, self).set_configuration(configuration=configuration, section=section)

        # Sub-class specific ...

        # Get the Picard tools Java Archive (JAR) class path directory.

        if configuration.config_parser.has_option(section=section, option='classpath_picard'):
            self.classpath_picard = configuration.config_parser.get(
                section=section,
                option='classpath_picard')

        if configuration.config_parser.has_option(section=section, option='include_non_pass_filter_reads'):
            self.include_non_pass_filter_reads = configuration.config_parser.getboolean(
                section=section,
                option='include_non_pass_filter_reads')

    def run(self):
        """Run the C{SamToFastq} C{Analysis} to convert a I{BAM} or I{SAM} file into I{FASTQ} files.
        """

        super(SamToFastq, self).run()

        default = Default.get_global_default()

        # Get the Picard tools Java Archive (JAR) class path directory.

        if not self.classpath_picard:
            self.classpath_picard = default.classpath_picard

        # Picard SamToFastq

        stf_drms = DRMS.from_analysis(
            name='sam_to_fastq',
            work_directory=self.project_directory,
            analysis=self)
        self.drms_list.append(stf_drms)

        for sample in self.samples:
            assert isinstance(sample, Sample)

            if self.debug > 0:
                print '{!r} Sample name: {}'.format(self, sample.name)
                print sample.trace(level=1)

            # bsf.data.Sample.get_all_paired_reads returns a Python dict of
            # Python str key and Python list of Python list objects
            # of bsf.data.PairedReads objects.

            replicate_dict = sample.get_all_paired_reads(replicate_grouping=False)

            replicate_keys = replicate_dict.keys()
            replicate_keys.sort(cmp=lambda x, y: cmp(x, y))

            for replicate_key in replicate_keys:
                assert isinstance(replicate_key, str)

                for paired_reads in replicate_dict[replicate_key]:
                    assert isinstance(paired_reads, PairedReads)

                    if self.debug > 0:
                        print '{!r} PairedReads name: {}'.format(self, paired_reads.get_name())

                    # Apply some sanity checks.

                    if paired_reads.reads2 and not paired_reads.reads1:
                        warnings.warn('PairedReads object with reads1 but no reads2 object.', UserWarning)
                        # TODO: Maybe this should check for BAM files and if there are none, write the FASTQ file to
                        # to the annotation sheet.
                        continue

                    reads = paired_reads.reads1
                    if reads.file_path[-4:] == '.bam':
                        pass
                        # Submit a conversion job.
                    else:
                        pass
                        # Write the line from the sample annotation sheet as is.

                    prefix = string.join(words=(stf_drms.name, replicate_key), sep='_')

                    file_path_dict = dict(
                        temporary_directory=string.join(words=(prefix, 'temporary'), sep='_'),
                        output_directory=string.join(words=(prefix, 'fastq'), sep='_')
                    )

                    runnable = Runnable(
                        name=prefix,
                        code_module='bsf.runnables.sam_to_fastq',
                        working_directory=self.project_directory,
                        file_path_dict=file_path_dict)
                    self.add_runnable(runnable=runnable)

                    java_process = Executable(name='sam_to_fastq', program='java', sub_command=Command(command=str()))
                    runnable.add_executable(executable=java_process)

                    java_process.add_switch_short(key='d64')
                    java_process.add_option_short(
                        key='jar',
                        value=os.path.join(self.classpath_picard, 'SamToFastq.jar'))
                    java_process.add_switch_short(key='Xmx2G')
                    java_process.add_option_pair(
                        key='-Djava.io.tmpdir',
                        value=file_path_dict['temporary_directory'])

                    # Set Picard SamToFastq options.

                    sub_command = java_process.sub_command

                    sub_command.add_option_pair(key='INPUT', value=paired_reads.reads1.file_path)
                    sub_command.add_option_pair(key='OUTPUT_PER_RG', value='true')
                    sub_command.add_option_pair(key='OUTPUT_DIR', value=file_path_dict['output_directory'])
                    if self.include_non_pass_filter_reads:
                        sub_command.add_option_pair(key='INCLUDE_NON_PF_READS', value='true')
                    else:
                        sub_command.add_option_pair(key='INCLUDE_NON_PF_READS', value='false')
                    sub_command.add_option_pair(key='TMP_DIR', value=runnable.file_path_dict['temporary_directory'])
                    sub_command.add_option_pair(key='VERBOSITY', value='WARNING')
                    sub_command.add_option_pair(key='QUIET', value='false')
                    sub_command.add_option_pair(key='VALIDATION_STRINGENCY', value='STRICT')
