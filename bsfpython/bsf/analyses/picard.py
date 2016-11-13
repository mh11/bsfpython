"""bsf.analyses.picard

A package of classes and methods modelling Picard analyses data files and data directories.
"""

#
# Copyright 2013 - 2016 Michael K. Schuster
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


import os
import warnings
import weakref

from bsf import Analysis, Runnable
from bsf.analyses.illumina_to_bam_tools import LibraryAnnotationSheet
from bsf.annotation import AnnotationSheet
from bsf.data import Reads, PairedReads, Sample, SampleAnnotationSheet
from bsf.illumina import RunFolder, RunFolderNotComplete
from bsf.process import RunnableStep, RunnableStepPicard, RunnableStepMakeDirectory
from bsf.standards import Default

import pysam


class PicardIlluminaRunFolder(Analysis):
    """The C{bsf.analyses.picard.PicardIlluminaRunFolder} class of Picard Analyses acting on Illumina Run Folders.

    Attributes:
    @cvar name: C{bsf.Analysis.name} that should be overridden by sub-classes
    @type name: str
    @cvar prefix: C{bsf.Analysis.prefix} that should be overridden by sub-classes
    @type prefix: str
    @cvar stage_name_lane: C{bsf.Stage.name} for the lane-specific stage
    @type stage_name_lane: str
    @ivar run_directory: File path to an I{Illumina Run Folder}
    @type run_directory: str | unicode
    @ivar intensity_directory: File path to the I{Intensities} directory,
        defaults to I{illumina_run_folder/Data/Intensities}
    @type intensity_directory: str | unicode
    @ivar basecalls_directory: File path to the I{BaseCalls} directory,
        defaults to I{illumina_run_folder/Data/Intensities/BaseCalls}
    @type basecalls_directory: str | unicode
    @ivar experiment_name: Experiment name (i.e. flow cell identifier) normally automatically read from
        Illumina Run Folder parameters
    @type experiment_name: str
    @ivar classpath_picard: Picard tools Java Archive (JAR) class path directory
    @type classpath_picard: str | unicode
    @ivar force: Force processing of incomplete Illumina Run Folders
    @type force: bool
    """

    name = "Picard PicardIlluminaRunFolder Analysis"
    prefix = "picard_illumina_run_folder"

    stage_name_lane = '_'.join((prefix, 'lane'))

    @classmethod
    def get_prefix_lane(cls, project_name, lane):
        """Get a Python C{str} for setting C{bsf.process.Executable.dependencies} in other C{bsf.Analysis} objects.

        @param project_name: A project name
        @type project_name: str
        @param lane: A lane number
        @type lane: str
        @return: The dependency string for a C{bsf.process.Executable} of this C{bsf.Analysis}
        @rtype: str
        """
        return '_'.join((cls.stage_name_lane, project_name, lane))

    def __init__(
            self,
            configuration=None,
            project_name=None,
            genome_version=None,
            input_directory=None,
            output_directory=None,
            project_directory=None,
            genome_directory=None,
            e_mail=None,
            debug=0,
            stage_list=None,
            collection=None,
            comparisons=None,
            samples=None,
            run_directory=None,
            intensity_directory=None,
            basecalls_directory=None,
            experiment_name=None,
            classpath_picard=None,
            force=False):
        """Initialise a C{bsf.analyses.picard.PicardIlluminaRunFolder} object.

        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param project_name: Project name
        @type project_name: str
        @param genome_version: Genome version
        @type genome_version: str
        @param input_directory: C{bsf.Analysis}-wide input directory
        @type input_directory: str
        @param output_directory: C{bsf.Analysis}-wide output directory
        @type output_directory: str
        @param project_directory: C{bsf.Analysis}-wide project directory,
            normally under the C{bsf.Analysis}-wide output directory
        @type project_directory: str
        @param genome_directory: C{bsf.Analysis}-wide genome directory,
            normally under the C{bsf.Analysis}-wide project directory
        @type genome_directory: str
        @param e_mail: e-Mail address for a UCSC Genome Browser Track Hub
        @type e_mail: str
        @param debug: Integer debugging level
        @type debug: int
        @param stage_list: Python C{list} of C{bsf.Stage} objects
        @type stage_list: list[bsf.Stage]
        @param collection: C{bsf.data.Collection}
        @type collection: bsf.data.Collection
        @param comparisons: Python C{dict} of Python C{tuple} objects of C{bsf.data.Sample} objects
        @type comparisons: dict[str, tuple[bsf.data.Sample]]
        @param samples: Python C{list} of C{bsf.data.Sample} objects
        @type samples: list[bsf.data.Sample]
        @param run_directory: File path to an I{Illumina Run Folder}
        @type run_directory: str | unicode
        @param intensity_directory: File path to the I{Intensities} directory,
            defaults to I{illumina_run_folder/Data/Intensities}
        @type intensity_directory: str | unicode
        @param basecalls_directory: File path to the I{BaseCalls} directory,
            defaults to I{illumina_run_folder/Data/Intensities/BaseCalls}
        @type basecalls_directory: str | unicode
        @param experiment_name: Experiment name (i.e. flow cell identifier) normally automatically read from
            Illumina Run Folder parameters
        @type experiment_name: str
        @param classpath_picard: Picard tools Java Archive (JAR) class path directory
        @type classpath_picard: str | unicode
        @param force: Force processing of incomplete Illumina Run Folders
        @type force: bool
        @return:
        @rtype:
        """

        super(PicardIlluminaRunFolder, self).__init__(
            configuration=configuration,
            project_name=project_name,
            genome_version=genome_version,
            input_directory=input_directory,
            output_directory=output_directory,
            project_directory=project_directory,
            genome_directory=genome_directory,
            e_mail=e_mail,
            debug=debug,
            stage_list=stage_list,
            collection=collection,
            comparisons=comparisons,
            samples=samples)

        if run_directory is None:
            self.run_directory = str()
        else:
            self.run_directory = run_directory

        if intensity_directory is None:
            self.intensity_directory = str()
        else:
            self.intensity_directory = intensity_directory

        if basecalls_directory is None:
            self.basecalls_directory = str()
        else:
            self.basecalls_directory = basecalls_directory

        if experiment_name is None:
            self.experiment_name = str()
        else:
            self.experiment_name = experiment_name

        if classpath_picard is None:
            self.classpath_picard = str()
        else:
            self.classpath_picard = classpath_picard

        if force is None:
            self.force = False
        else:
            assert isinstance(force, bool)
            self.force = force

        self._irf = None

        return

    def set_configuration(self, configuration, section):
        """Set instance variables of a C{bsf.analyses.picard.PicardIlluminaRunFolder} object via a section of a
        C{bsf.standards.Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param section: Configuration file section
        @type section: str
        @return:
        @rtype:
        """

        super(PicardIlluminaRunFolder, self).set_configuration(configuration=configuration, section=section)

        # Sub-class specific ...

        # Get Illumina Run Folder information.

        option = 'illumina_run_folder'
        if configuration.config_parser.has_option(section=section, option=option):
            self.run_directory = configuration.config_parser.get(section=section, option=option)

        option = 'intensity_directory'
        if configuration.config_parser.has_option(section=section, option=option):
            self.intensity_directory = configuration.config_parser.get(section=section, option=option)

        option = 'basecalls_directory'
        if configuration.config_parser.has_option(section=section, option=option):
            self.basecalls_directory = configuration.config_parser.get(section=section, option=option)

        # Get the experiment name.

        option = 'experiment_name'
        if configuration.config_parser.has_option(section=section, option=option):
            self.experiment_name = configuration.config_parser.get(section=section, option=option)

        # Get the Picard tools Java Archive (JAR) class path directory.

        option = 'classpath_picard'
        if configuration.config_parser.has_option(section=section, option=option):
            self.classpath_picard = configuration.config_parser.get(section=section, option=option)

        option = 'force'
        if configuration.config_parser.has_option(section=section, option=option):
            self.force = configuration.config_parser.getboolean(section=section, option=option)

        return

    def run(self):
        """Run the C{bsf.analyses.picard.PicardIlluminaRunFolder} C{bsf.Analysis}.

        @return:
        @rtype:
        """

        default = Default.get_global_default()

        # Define an Illumina Run Folder directory.
        # Expand an eventual user part i.e. on UNIX ~ or ~user and
        # expand any environment variables i.e. on UNIX ${NAME} or $NAME
        # Check if an absolute path has been provided, if not,
        # automatically prepend standard BSF directory paths.

        if not self.run_directory:
            raise Exception('An Illumina run directory or file path has not been defined.')

        self.run_directory = Default.get_absolute_path(
            file_path=self.run_directory,
            default_path=Default.absolute_runs_illumina())

        # Check that the Illumina Run Folder exists.

        if not os.path.isdir(self.run_directory):
            raise Exception(
                'The Illumina run directory {!r} does not exist.'.format(self.run_directory))

        # Check that the Illumina Run Folder is complete.

        if not (os.path.exists(path=os.path.join(self.run_directory, 'RTAComplete.txt')) or self.force):
            raise RunFolderNotComplete(
                'The Illumina run directory {!r} is not complete.'.format(self.run_directory))

        # Define an 'Intensities' directory.
        # Expand an eventual user part i.e. on UNIX ~ or ~user and
        # expand any environment variables i.e. on UNIX ${NAME} or $NAME
        # Check if an absolute path has been provided, if not,
        # automatically prepend the Illumina Run Folder path.

        if self.intensity_directory:
            self.intensity_directory = Default.get_absolute_path(
                file_path=self.intensity_directory,
                default_path=self.run_directory)
        else:
            self.intensity_directory = os.path.join(self.run_directory, 'Data', 'Intensities')

        # Check that the Intensities directory exists.

        if not os.path.isdir(self.intensity_directory):
            raise Exception(
                'The Intensity directory {!r} does not exist.'.format(self.intensity_directory))

        # Define a 'BaseCalls' directory.
        # Expand an eventual user part i.e. on UNIX ~ or ~user and
        # expand any environment variables i.e. on UNIX ${NAME} or $NAME
        # Check if an absolute path has been provided, if not,
        # automatically prepend the Intensities directory path.

        if self.basecalls_directory:
            self.basecalls_directory = Default.get_absolute_path(
                file_path=self.basecalls_directory,
                default_path=self.intensity_directory)
        else:
            self.basecalls_directory = os.path.join(self.intensity_directory, 'BaseCalls')

        # Check that the BaseCalls directory exists.

        if not os.path.isdir(self.basecalls_directory):
            raise Exception(
                'The BaseCalls directory {!r} does not exist.'.format(self.basecalls_directory))

        self._irf = RunFolder.from_file_path(file_path=self.run_directory)

        # The experiment name (e.g. BSF_0000) is used as the prefix for archive BAM files.
        # Read it from the configuration file or from the
        # Run Parameters of the Illumina Run Folder.

        if not self.experiment_name:
            self.experiment_name = self._irf.run_parameters.get_experiment_name

        # The project name is a concatenation of the experiment name and the Illumina flow cell identifier.
        # In case it has not been specified in the configuration file, read it from the
        # Run Information of the Illumina Run Folder.

        if not self.project_name:
            self.project_name = '_'.join((self.experiment_name, self._irf.run_information.flow_cell))

        # Get the Picard tools Java Archive (JAR) class path directory.

        if not self.classpath_picard:
            self.classpath_picard = default.classpath_picard

        # Call the run method of the super class after the project_name has been defined.

        super(PicardIlluminaRunFolder, self).run()

        return


class ExtractIlluminaBarcodesSheet(AnnotationSheet):
    """The C{bsf.analyses.picard.ExtractIlluminaBarcodesSheet} class represents a
    Tab-Separated Value (TSV) table of library information for the
    C{bsf.analyses.picard.ExtractIlluminaBarcodes} C{bsf.Analysis}.

    Attributes:
    @cvar _file_type: File type (i.e. I{excel} or I{excel-tab} defined in the C{csv.Dialect} class)
    @type _file_type: str
    @cvar _header_line: Header line exists
    @type _header_line: bool
    @cvar _field_names: Python C{list} of Python C{str} (field name) objects
    @type _field_names: list[str]
    @cvar _test_methods: Python C{dict} of Python C{str} (field name) key data and
        Python C{list} of Python C{function} value data
    @type _test_methods: dict[str, list[function]]
    """

    _file_type = 'excel-tab'

    _header_line = True

    _field_names = [
        'barcode_sequence_1',
        'barcode_sequence_2',
        'barcode_name',
        'library_name',
    ]

    _test_methods = dict()


class IlluminaBasecallsToSamSheet(AnnotationSheet):
    """The C{bsf.analyses.picard.IlluminaBasecallsToSamSheet} class represents a
    Tab-Separated Value (TSV) table of library information for the
    C{bsf.analyses.picard.ExtractIlluminaBarcodes} C{bsf.Analysis}.

    Attributes:
    @cvar _file_type: File type (i.e. I{excel} or I{excel-tab} defined in the C{csv.Dialect} class)
    @type _file_type: str
    @cvar _header_line: Header line exists
    @type _header_line: bool
    @cvar _field_names: Python C{list} of Python C{str} (field name) objects
    @type _field_names: list[str]
    @cvar _test_methods: Python C{dict} of Python C{str} (field name) key data and
        Python C{list} of Python C{function} value data
    @type _test_methods: dict[str, list[function]]
    """

    _file_type = 'excel-tab'

    _header_line = True

    _field_names = [
        'OUTPUT',
        'SAMPLE_ALIAS',
        'LIBRARY_NAME',
        'BARCODE_1',
        'BARCODE_2',
    ]

    _test_methods = dict()


class ExtractIlluminaRunFolder(PicardIlluminaRunFolder):
    """The C{bsf.analyses.picard.ExtractIlluminaRunFolder} class represents to extract data from an Illumina Run Folder.

    The analysis is based on Picard ExtractIlluminaBarcodes and Picard IlluminaBasecallsToSam.

    Attributes:
    @cvar name: C{bsf.Analysis.name} that should be overridden by sub-classes
    @type name: str
    @cvar prefix: C{bsf.Analysis.prefix} that should be overridden by sub-classes
    @type prefix: str
    @cvar stage_name_lane: C{bsf.Stage.name} for the lane-specific stage
    @type stage_name_lane: str
    @ivar samples_directory: BSF samples directory
    @type samples_directory: str | unicode
    @ivar experiment_directory: Experiment directory
    @type experiment_directory: str | unicode
    @ivar library_path: Library annotation file path
    @type library_path: str | unicode
    @ivar max_mismatches: Maximum number of mismatches
    @type max_mismatches: str
    @ivar min_base_quality: Minimum base quality
    @type min_base_quality: str
    @ivar sequencing_centre: Sequencing centre
    @type sequencing_centre: str
    """

    name = "Picard ExtractIlluminaRunFolder Analysis"
    prefix = "extract_illumina_run_folder"

    stage_name_lane = '_'.join((prefix, 'lane'))

    def __init__(
            self,
            configuration=None,
            project_name=None,
            genome_version=None,
            input_directory=None,
            output_directory=None,
            project_directory=None,
            genome_directory=None,
            e_mail=None,
            debug=0,
            stage_list=None,
            collection=None,
            comparisons=None,
            samples=None,
            run_directory=None,
            intensity_directory=None,
            basecalls_directory=None,
            experiment_name=None,
            classpath_picard=None,
            force=False,
            samples_directory=None,
            experiment_directory=None,
            library_path=None,
            max_mismatches=None,
            min_base_quality=None,
            sequencing_centre=None):
        """Initialise a C{bsf.analyses.picard.ExtractIlluminaRunFolder} object.

        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param project_name: Project name
        @type project_name: str
        @param genome_version: Genome version
        @type genome_version: str
        @param input_directory: C{bsf.Analysis}-wide input directory
        @type input_directory: str
        @param output_directory: C{bsf.Analysis}-wide output directory
        @type output_directory: str
        @param project_directory: C{bsf.Analysis}-wide project directory,
            normally under the C{bsf.Analysis}-wide output directory
        @type project_directory: str
        @param genome_directory: C{bsf.Analysis}-wide genome directory,
            normally under the C{bsf.Analysis}-wide project directory
        @type genome_directory: str
        @param e_mail: e-Mail address for a UCSC Genome Browser Track Hub
        @type e_mail: str
        @param debug: Integer debugging level
        @type debug: int
        @param stage_list: Python C{list} of C{bsf.Stage} objects
        @type stage_list: list[bsf.Stage]
        @param collection: C{bsf.data.Collection}
        @type collection: bsf.data.Collection
        @param comparisons: Python C{dict} of Python C{tuple} objects of C{bsf.data.Sample} objects
        @type comparisons: dict[str, tuple[bsf.data.Sample]]
        @param samples: Python C{list} of C{bsf.data.Sample} objects
        @type samples: list[bsf.data.Sample]
        @param run_directory: File path to an I{Illumina Run Folder}
        @type run_directory: str | unicode
        @param intensity_directory: File path to the I{Intensities} directory,
            defaults to I{illumina_run_folder/Data/Intensities}
        @type intensity_directory: str | unicode
        @param basecalls_directory: File path to the I{BaseCalls} directory,
            defaults to I{illumina_run_folder/Data/Intensities/BaseCalls}
        @type basecalls_directory: str | unicode
        @param experiment_name: Experiment name (i.e. flow cell identifier) normally automatically read from
            Illumina Run Folder parameters
        @type experiment_name: str
        @param classpath_picard: Picard tools Java Archive (JAR) class path directory
        @type classpath_picard: str | unicode
        @param force: Force processing of incomplete Illumina Run Folders
        @type force: bool
        @param samples_directory: BSF samples directory
        @type samples_directory: str | unicode
        @param experiment_directory: Experiment directory
        @type experiment_directory: str | unicode
        @param library_path: Library annotation file path
        @type library_path: str | unicode
        @param max_mismatches: Maximum number of mismatches
        @type max_mismatches: str
        @param min_base_quality: Minimum base quality
        @type min_base_quality: str
        @param sequencing_centre: Sequencing centre
        @type sequencing_centre: str
        @return:
        @rtype:
        """

        super(ExtractIlluminaRunFolder, self).__init__(
            configuration=configuration,
            project_name=project_name,
            genome_version=genome_version,
            input_directory=input_directory,
            output_directory=output_directory,
            project_directory=project_directory,
            genome_directory=genome_directory,
            e_mail=e_mail,
            debug=debug,
            stage_list=stage_list,
            collection=collection,
            comparisons=comparisons,
            samples=samples,
            run_directory=run_directory,
            intensity_directory=intensity_directory,
            basecalls_directory=basecalls_directory,
            experiment_name=experiment_name,
            classpath_picard=classpath_picard,
            force=force)

        if samples_directory is None:
            self.samples_directory = str()
        else:
            self.samples_directory = samples_directory

        if experiment_directory is None:
            self.experiment_directory = str()
        else:
            self.experiment_directory = experiment_directory

        if library_path is None:
            self.library_path = str()
        else:
            self.library_path = library_path

        if max_mismatches is None:
            self.max_mismatches = str()
        else:
            self.max_mismatches = max_mismatches

        if min_base_quality is None:
            self.min_base_quality = str()
        else:
            self.min_base_quality = min_base_quality

        if sequencing_centre is None:
            self.sequencing_centre = str()
        else:
            self.sequencing_centre = sequencing_centre

        return

    def set_configuration(self, configuration, section):
        """Set instance variables of a C{bsf.analyses.picard.ExtractIlluminaRunFolder} object via a section of a
        C{bsf.standards.Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param section: Configuration file section
        @type section: str
        @return:
        @rtype:
        """

        super(ExtractIlluminaRunFolder, self).set_configuration(configuration=configuration, section=section)

        # Sub-class specific ...

        # Get the general samples directory.

        option = 'samples_directory'
        if configuration.config_parser.has_option(section=section, option=option):
            self.samples_directory = configuration.config_parser.get(section=section, option=option)

        # For the moment, the experiment_directory cannot be configured.
        # It is automatically assembled from self.samples_directory and self.project_name by the run() method.

        # Get the library annotation file.

        option = 'library_path'
        if configuration.config_parser.has_option(section=section, option=option):
            self.library_path = configuration.config_parser.get(section=section, option=option)

        # Get the maximum number of mismatches.

        option = 'max_mismatches'
        if configuration.config_parser.has_option(section=section, option=option):
            self.max_mismatches = configuration.config_parser.get(section=section, option=option)

        # Get the minimum base quality.

        option = 'min_base_quality'
        if configuration.config_parser.has_option(section=section, option=option):
            self.min_base_quality = configuration.config_parser.get(section=section, option=option)

        # Get sequencing centre information.

        option = 'sequencing_centre'
        if configuration.config_parser.has_option(section=section, option=option):
            self.sequencing_centre = configuration.config_parser.get(section=section, option=option)

        return

    def run(self):
        """Run a C{bsf.analyses.picard.ExtractIlluminaRunFolder} C{bsf.Analysis}.

        @return:
        @rtype:
        """

        super(ExtractIlluminaRunFolder, self).run()

        default = Default.get_global_default()

        self.samples_directory = Default.get_absolute_path(
            file_path=self.samples_directory,
            default_path=Default.absolute_samples())

        # As a safety measure, to prevent creation of rogue directory paths, the samples_directory has to exist.

        if not os.path.isdir(self.samples_directory):
            raise Exception(
                'The ExtractIlluminaRunFolder samples_directory {!r} does not exist.'.format(self.samples_directory))

        self.experiment_directory = os.path.join(self.samples_directory, self.project_name)

        # Get sequencing centre information.

        if not self.sequencing_centre:
            self.sequencing_centre = default.operator_sequencing_centre

        # Get the library annotation sheet.
        # The library annotation sheet is deliberately not passed in via sas_file,
        # as the Analysis.run() method reads that option into a BSF Collection object.

        self.library_path = os.path.expanduser(path=self.library_path)
        self.library_path = os.path.expandvars(path=self.library_path)

        if not self.library_path:
            self.library_path = '_'.join((self.project_name, 'libraries.csv'))

        self.library_path = os.path.normpath(path=self.library_path)

        if not os.path.exists(path=self.library_path):
            raise Exception('Library annotation file {!r} does not exist.'.format(self.library_path))

        # Read the LibraryAnnotationSheet and populate a flow cell dict indexed on the lane number ...
        # FIXME: Differences to BamIndexDecoder. No validation for the moment.
        flow_cell_dict = dict()

        library_annotation_sheet = LibraryAnnotationSheet.from_file_path(file_path=self.library_path)

        for row_dict in library_annotation_sheet.row_dicts:
            if row_dict['lane'] not in flow_cell_dict:
                flow_cell_dict[row_dict['lane']] = list()

            flow_cell_dict[row_dict['lane']].append(row_dict)

        # Create a Sample Annotation Sheet in the project directory and
        # eventually transfer it into the experiment_directory.
        sample_annotation_name = '_'.join((self.project_name, 'samples.csv'))
        sample_annotation_sheet = SampleAnnotationSheet(
            file_path=os.path.join(self.project_directory, sample_annotation_name))

        stage_lane = self.get_stage(name=self.stage_name_lane)

        # For each lane in the flow_cell_dict ...
        # TODO: For the moment this depends on the lanes (keys) defined in the LibraryAnnotationSheet.
        # Not all lanes may thus get extracted.

        keys = flow_cell_dict.keys()
        keys.sort(cmp=lambda x, y: cmp(x, y))

        for key in keys:
            assert isinstance(key, str)

            # The key represents the lane number as a Python str.
            file_path_dict_lane = {
                'output_directory': '_'.join((self.project_name, key, 'output')),
                'samples_directory': '_'.join((self.project_name, key, 'samples')),
                'barcode_tsv': '_'.join((self.project_name, key, 'barcode.tsv')),
                'metrics_tsv': '_'.join((self.project_name, key, 'metrics.tsv')),
                'library_tsv': '_'.join((self.project_name, key, 'library.tsv')),
            }

            # BARCODE_FILE
            eib_sheet = ExtractIlluminaBarcodesSheet(
                file_path=os.path.join(self.project_directory, file_path_dict_lane['barcode_tsv']))

            # LIBRARY_PARAMS
            ibs_sheet = IlluminaBasecallsToSamSheet(
                file_path=os.path.join(self.project_directory, file_path_dict_lane['library_tsv']))

            # Initialise a list of barcode sequence lengths.
            bc_length_list = list()

            # Sort each lane by sample name.
            flow_cell_dict_list = flow_cell_dict[key]
            assert isinstance(flow_cell_dict_list, list)
            flow_cell_dict_list.sort(cmp=lambda x, y: cmp(x['sample_name'], y['sample_name']))

            for row_dict in flow_cell_dict_list:
                assert isinstance(row_dict, dict)
                # Determine and check the length of the barcode sequences.
                for index in range(0L, 1L + 1L):
                    if len(bc_length_list) == index:
                        # If this is the first barcode, assign it.
                        bc_length_list.append(len(row_dict['barcode_sequence_' + str(index + 1L)]))
                    else:
                        # If this a subsequent barcode, check it.
                        bc_length = len(row_dict['barcode_sequence_' + str(index + 1L)])
                        if bc_length != bc_length_list[index]:
                            # Barcode lengths do not match ...
                            warnings.warn(
                                'The length ({}) of barcode {} {!r} does not match '
                                'the length ({}) of previous barcodes.'.format(
                                    bc_length,
                                    index + 1L,
                                    row_dict['barcode_sequence_' + str(index + 1L)],
                                    bc_length_list[index]),
                                UserWarning)

                # Add a row to the lane-specific Picard ExtractIlluminaBarcodesSheet.

                eib_sheet.row_dicts.append({
                    'barcode_sequence_1': row_dict['barcode_sequence_1'],
                    'barcode_sequence_2': row_dict['barcode_sequence_2'],
                    'barcode_name': row_dict['sample_name'],
                    'library_name': row_dict['library_name'],
                })

                # Add a row to the lane-specific Picard IlluminaBasecallsToSamSheet.

                ibs_sheet.row_dicts.append({
                    'BARCODE_1': row_dict['barcode_sequence_1'],
                    'BARCODE_2': row_dict['barcode_sequence_2'],
                    'OUTPUT': os.path.join(
                        file_path_dict_lane['samples_directory'],
                        '{}_{}#{}.bam'.format(self.project_name, key, row_dict['sample_name'])),
                    'SAMPLE_ALIAS': row_dict['sample_name'],
                    'LIBRARY_NAME': row_dict['library_name'],
                })

                # Add a row to the flow cell-specific sample annotation sheet.

                sample_annotation_sheet.row_dicts.append({
                    'File Type': 'Automatic',
                    'ProcessedRunFolder Name': self.project_name,
                    'Project Name': row_dict['library_name'],
                    'Project Size': row_dict['library_size'],
                    'Sample Name': row_dict['sample_name'],
                    'PairedReads Index 1': row_dict['barcode_sequence_1'],
                    'PairedReads Index 2': row_dict['barcode_sequence_2'],
                    # TODO: It would be good to add a RunnableStep to populate the ReadGroup.
                    'PairedReads ReadGroup': '',
                    'Reads1 Name': '_'.join((self.project_name, key, row_dict['sample_name'])),
                    'Reads1 File': os.path.join(
                        os.path.basename(self.experiment_directory),
                        file_path_dict_lane['samples_directory'],
                        '{}_{}#{}.bam'.format(self.project_name, key, row_dict['sample_name'])),
                    'Reads2 Name': '',
                    'Reads2 File': '',
                })

            # The IlluminaBasecallsToSamSheet needs adjusting ...

            if len(ibs_sheet.row_dicts) == 1 and len(ibs_sheet.row_dicts[0]['BARCODE_1']) == 0 and len(
                    ibs_sheet.row_dicts[0]['BARCODE_2']) == 0:
                # ... if a single sample, but neither BARCODE_1 nor BARCODE_2 were defined,
                # BARCODE_1 needs setting to 'N'.
                ibs_sheet.row_dicts[0]['BARCODE_1'] = 'N'
            else:
                # ... in all other cases as a last row for unmatched barcode sequences needs adding.
                ibs_sheet.row_dicts.append({
                    'BARCODE_1': 'N',
                    'BARCODE_2': '',
                    'OUTPUT': os.path.join(
                        file_path_dict_lane['samples_directory'],
                        '{}_{}#0.bam'.format(self.project_name, key)),
                    'SAMPLE_ALIAS': 'Unmatched',
                    'LIBRARY_NAME': ibs_sheet.row_dicts[0]['LIBRARY_NAME'],
                })

            # Calculate the read structure string from the IRF and the bc_length_list above ...

            read_structure = str()
            index_read_index = 0L  # Number of index reads.
            assert isinstance(self._irf, RunFolder)
            # Instantiate and sort a new list of RunInformationRead objects.
            run_information_read_list = list(self._irf.run_information.reads)
            run_information_read_list.sort(cmp=lambda x, y: cmp(x.number, y.number))
            for run_information_read in run_information_read_list:
                if run_information_read.index:
                    # For an index read ...
                    read_structure += '{}B'.format(bc_length_list[index_read_index])
                    if run_information_read.cycles < bc_length_list[index_read_index]:
                        read_structure += '{}S'.format(run_information_read.cycles - bc_length_list[index_read_index])
                    index_read_index += 1  # Increment to the next barcode read
                else:
                    # For a template read ...
                    read_structure += '{}T'.format(run_information_read.cycles)

            # Further adjust the IlluminaBaseCallsToSamSheet and remove any BARCODE_N columns not represented
            # in the read structure.

            for index in range(0L, 1L + 1L):
                if index + 1L > index_read_index:
                    # Remove the 'BARCODE_N' filed from the list of field names.
                    if 'BARCODE_' + str(index + 1L) in ibs_sheet.field_names:
                        ibs_sheet.field_names.remove('BARCODE_' + str(index + 1L))
                    # Remove the 'BARCODE_N' entry form each row dict object, since csv.DictWriter requires it.
                    for row_dict in ibs_sheet.row_dicts:
                        row_dict.pop('BARCODE_' + str(index + 1L), None)

            # Write the lane-specific Picard ExtractIlluminaBarcodesSheet and Picard IlluminaBasecallsToSamSheet.

            if index_read_index > 0L:
                eib_sheet.to_file_path()

            ibs_sheet.to_file_path()

            # Create a Runnable and Executable for the lane stage.

            runnable_lane = self.add_runnable(
                runnable=Runnable(
                    name=self.get_prefix_lane(project_name=self.project_name, lane=key),
                    code_module='bsf.runnables.generic',
                    working_directory=self.project_directory,
                    file_path_dict=file_path_dict_lane))
            self.set_stage_runnable(
                stage=stage_lane,
                runnable=runnable_lane)

            # Create an output_directory in the project_directory.

            runnable_lane.add_runnable_step(
                runnable_step=RunnableStepMakeDirectory(
                    name='make_output_directory',
                    directory_path=file_path_dict_lane['output_directory']))

            # Create a samples_directory in the project_directory.

            runnable_lane.add_runnable_step(
                runnable_step=RunnableStepMakeDirectory(
                    name='make_samples_directory',
                    directory_path=file_path_dict_lane['samples_directory']))

            # Create a RunnableStep for Picard ExtractIlluminaBarcodes, only if index (barcode) reads are present.

            if index_read_index > 0L:
                runnable_step = runnable_lane.add_runnable_step(
                    runnable_step=RunnableStepPicard(
                        name='picard_extract_illumina_barcodes',
                        java_temporary_path=runnable_lane.get_relative_temporary_directory_path,
                        java_heap_maximum='Xmx2G',
                        picard_classpath=self.classpath_picard,
                        picard_command='ExtractIlluminaBarcodes'))
                assert isinstance(runnable_step, RunnableStepPicard)
                runnable_step.add_picard_option(key='BASECALLS_DIR', value=self.basecalls_directory)
                runnable_step.add_picard_option(key='OUTPUT_DIR', value=file_path_dict_lane['output_directory'])
                runnable_step.add_picard_option(key='LANE', value=key)
                runnable_step.add_picard_option(key='READ_STRUCTURE', value=read_structure)
                runnable_step.add_picard_option(key='BARCODE_FILE', value=file_path_dict_lane['barcode_tsv'])
                runnable_step.add_picard_option(key='METRICS_FILE', value=file_path_dict_lane['metrics_tsv'])
                if self.max_mismatches:
                    # Maximum mismatches for a barcode to be considered a match. Default value: 1.
                    runnable_step.add_picard_option(key='MAX_MISMATCHES', value=self.max_mismatches)
                # MIN_MISMATCH_DELTA: Minimum difference between number of mismatches in the best and
                # second best barcodes for a barcode to be considered a match. Default value: 1.
                # MAX_NO_CALLS Maximum allowable number of no-calls in a barcode read before it is
                # considered unmatchable. Default value: 2.
                if self.min_base_quality:
                    # Minimum base quality. Any barcode bases falling below this quality will be considered
                    # a mismatch even in the bases match. Default value: 0.
                    runnable_step.add_picard_option(key='MINIMUM_BASE_QUALITY', value=self.min_base_quality)
                # MINIMUM_QUALITY The minimum quality (after transforming 0s to 1s) expected from reads.
                # If qualities are lower than this value, an error is thrown.The default of 2 is what the
                # Illumina's spec describes as the minimum, but in practice the value has been observed lower.
                # Default value: 2.
                runnable_step.add_picard_option(key='COMPRESS_OUTPUTS', value='true')
                runnable_step.add_picard_option(key='NUM_PROCESSORS', value=str(stage_lane.threads))
                runnable_step.add_picard_option(
                    key='TMP_DIR',
                    value=runnable_lane.get_relative_temporary_directory_path)

            # Picard IlluminaBasecallsToSam

            # Create a RunnableStep for Picard IlluminaBasecallsToSam.

            runnable_step = runnable_lane.add_runnable_step(
                runnable_step=RunnableStepPicard(
                    name='picard_illumina_basecalls_to_sam',
                    java_temporary_path=runnable_lane.get_relative_temporary_directory_path,
                    java_heap_maximum='Xmx2G',
                    picard_classpath=self.classpath_picard,
                    picard_command='IlluminaBasecallsToSam'))
            assert isinstance(runnable_step, RunnableStepPicard)
            runnable_step.add_picard_option(key='BASECALLS_DIR', value=self.basecalls_directory)
            if index_read_index > 0L:
                runnable_step.add_picard_option(key='BARCODES_DIR', value=file_path_dict_lane['output_directory'])
            runnable_step.add_picard_option(key='LANE', value=key)
            # OUTPUT is deprecated.
            # TODO: Does the RUN_BARCODE work???
            runnable_step.add_picard_option(key='RUN_BARCODE', value=self._irf.run_parameters.get_flow_cell_barcode)
            # SAMPLE_ALIAS is deprecated.
            runnable_step.add_picard_option(key='READ_GROUP_ID', value='{}_{}'.format(self.project_name, key))
            # LIBRARY_NAME is deprecated.
            runnable_step.add_picard_option(key='SEQUENCING_CENTER', value=self.sequencing_centre)
            # NOTE: The ISO date format still does not work for Picard tools 2.6.1. Sigh.
            # runnable_step.add_picard_option(key='RUN_START_DATE', value=self._irf.run_information.get_iso_date)
            # NOTE: The only date format that seems to work is mm/dd/yyyy. Sigh.
            runnable_step.add_picard_option(key='RUN_START_DATE', value='{}/{}/20{}'.format(
                self._irf.run_information.date[2:4],
                self._irf.run_information.date[4:6],
                self._irf.run_information.date[0:2]))
            # PLATFORM The name of the sequencing technology that produced the read. Default value: illumina.
            # FIXME: IlluminaToBam defaults to 'ILLUMINA'.
            # runnable_step.add_picard_option(key='PLATFORM', value='ILLUMINA')
            runnable_step.add_picard_option(key='READ_STRUCTURE', value=read_structure)
            runnable_step.add_picard_option(key='LIBRARY_PARAMS', value=file_path_dict_lane['library_tsv'])
            # runnable_step.add_picard_option(key='ADAPTERS_TO_CHECK', value='')  # TODO: ???
            runnable_step.add_picard_option(key='NUM_PROCESSORS', value=str(stage_lane.threads))
            # FIRST_TILE
            # TILE_LIMIT
            # FORCE_GC
            # APPLY_EAMSS_FILTER
            # MAX_READS_IN_RAM_PER_TILE
            # MINIMUM_QUALITY
            # INCLUDE_NON_PF_READS  # FIXME: Set this to the filter section in the configuration file.
            # IGNORE_UNEXPECTED_BARCODES
            # MOLECULAR_INDEX_TAG
            # MOLECULAR_INDEX_BASE_QUALITY_TAG
            # TAG_PER_MOLECULAR_INDEX
            runnable_step.add_picard_option(key='TMP_DIR', value=runnable_lane.get_relative_temporary_directory_path)
            runnable_step.add_picard_option(key='COMPRESSION_LEVEL', value='9')
            runnable_step.add_picard_option(key='CREATE_MD5_FILE', value='true')

        # Finally, write the flow cell-specific SampleAnnotationSheet to the internal file path.

        sample_annotation_sheet.to_file_path()

        return


class CollectHiSeqXPfFailMetrics(PicardIlluminaRunFolder):
    """The C{bsf.analyses.picard.CollectHiSeqXPfFailMetrics} class represents Picard CollectHiSeqXPfFailMetrics.

    Attributes:
    @cvar name: C{bsf.Analysis.name} that should be overridden by sub-classes
    @type name: str
    @cvar prefix: C{bsf.Analysis.prefix} that should be overridden by sub-classes
    @type prefix: str
    @cvar stage_name_lane: C{bsf.Stage.name} for the lane-specific stage
    @type stage_name_lane: str
    """

    name = "Picard CollectHiSeqXPfFailMetrics Analysis"
    prefix = "picard_hiseq_x_pf_fail"

    stage_name_lane = '_'.join((prefix, 'lane'))

    def run(self):
        """Run the C{bsf.analyses.picard.CollectHiSeqXPfFailMetrics} C{bsf.Analysis}.

        @return:
        @rtype:
        """

        super(CollectHiSeqXPfFailMetrics, self).run()

        # Picard CollectHiSeqXPfFailMetrics

        stage_lane = self.get_stage(name=self.stage_name_lane)

        cell_dependency_list = list()

        for lane_int in range(0 + 1, self._irf.run_information.flow_cell_layout.lane_count + 1):
            lane_str = str(lane_int)

            lane_prefix = self.get_prefix_lane(
                project_name=self.project_name,
                lane=lane_str)

            file_path_dict_lane = {
                'summary_tsv': lane_prefix + '.pffail_summary_metrics',
                'detailed_tsv': lane_prefix + '.pffail_detailed_metrics',
            }

            # NOTE: The Runnable.name has to match the Executable.name that gets submitted via the Stage.
            runnable_lane = self.add_runnable(
                runnable=Runnable(
                    name=self.get_prefix_lane(
                        project_name=self.project_name,
                        lane=lane_str),
                    code_module='bsf.runnables.generic',
                    working_directory=self.project_directory,
                    file_path_dict=file_path_dict_lane))

            executable_lane = self.set_stage_runnable(
                stage=stage_lane,
                runnable=runnable_lane)

            # Add the dependency for the cell-specific process.

            cell_dependency_list.append(executable_lane.name)

            runnable_step = runnable_lane.add_runnable_step(
                runnable_step=RunnableStepPicard(
                    name='illumina_to_bam',
                    java_temporary_path=runnable_lane.get_relative_temporary_directory_path,
                    java_heap_maximum='Xmx4G',
                    picard_classpath=self.classpath_picard,
                    picard_command='CollectHiSeqXPfFailMetrics'))
            assert isinstance(runnable_step, RunnableStepPicard)
            # BASECALLS_DIR is required.
            runnable_step.add_picard_option(key='BASECALLS_DIR', value=self.basecalls_directory)
            # OUTPUT is required.
            runnable_step.add_picard_option(key='OUTPUT', value=lane_prefix)
            # LANE is required.
            runnable_step.add_picard_option(key='LANE', value=lane_str)
            # NUM_PROCESSORS defaults to '1'.
            runnable_step.add_picard_option(key='NUM_PROCESSORS', value=str(stage_lane.threads))
            # N_CYCLES defaults to '24'. Should match Illumina RTA software.

        return


class SamToFastq(Analysis):
    """The C{bsf.analyses.picard.SamToFastq} class represents the logic to run the Picard SamToFastq analysis.

    Attributes:

    @cvar name: C{bsf.Analysis.name} that should be overridden by sub-classes
    @type name: str
    @cvar prefix: C{bsf.Analysis.prefix} that should be overridden by sub-classes
    @type prefix: str
    @ivar classpath_picard: Picard tools Java Archive (JAR) class path directory
    @type classpath_picard: str | unicode
    @ivar include_non_pf_reads: Include non-pass filer reads
    @type include_non_pf_reads: bool
    """

    name = 'Picard SamToFastq Analysis'
    prefix = 'picard_sam_to_fastq'

    def __init__(
            self,
            configuration=None,
            project_name=None,
            genome_version=None,
            input_directory=None,
            output_directory=None,
            project_directory=None,
            genome_directory=None,
            e_mail=None,
            debug=0,
            stage_list=None,
            collection=None,
            comparisons=None,
            samples=None,
            classpath_picard=None,
            include_non_pf_reads=False):
        """Initialise a C{bsf.analyses.picard.SamToFastq} object.

        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param project_name: Project name
        @type project_name: str
        @param genome_version: Genome version
        @type genome_version: str
        @param input_directory: C{bsf.Analysis}-wide input directory
        @type input_directory: str
        @param output_directory: C{bsf.Analysis}-wide output directory
        @type output_directory: str
        @param project_directory: C{bsf.Analysis}-wide project directory,
            normally under the C{bsf.Analysis}-wide output directory
        @type project_directory: str
        @param genome_directory: C{bsf.Analysis}-wide genome directory,
            normally under the C{bsf.Analysis}-wide project directory
        @type genome_directory: str
        @param e_mail: e-Mail address for a UCSC Genome Browser Track Hub
        @type e_mail: str
        @param debug: Integer debugging level
        @type debug: int
        @param stage_list: Python C{list} of C{bsf.Stage} objects
        @type stage_list: list[bsf.Stage]
        @param collection: C{bsf.data.Collection}
        @type collection: bsf.data.Collection
        @param comparisons: Python C{dict} of Python C{tuple} objects of C{bsf.data.Sample} objects
        @type comparisons: dict[str, tuple[bsf.data.Sample]]
        @param samples: Python C{list} of C{bsf.data.Sample} objects
        @type samples: list[bsf.data.Sample]
        @param classpath_picard: Picard tools Java Archive (JAR) class path directory
        @type classpath_picard: str | unicode
        @param include_non_pf_reads: Include non-pass filer reads
        @type include_non_pf_reads: bool
        @return:
        @rtype:
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
            stage_list=stage_list,
            collection=collection,
            comparisons=comparisons,
            samples=samples)

        if classpath_picard is None:
            self.classpath_picard = str()
        else:
            self.classpath_picard = classpath_picard

        if include_non_pf_reads is None:
            self.include_non_pass_filter_reads = False
        else:
            assert isinstance(include_non_pf_reads, bool)
            self.include_non_pass_filter_reads = include_non_pf_reads

        return

    def set_configuration(self, configuration, section):
        """Set instance variables of a C{bsf.analyses.picard.SamToFastq} object via a section of a
        C{bsf.standards.Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: C{bsf.standards.Configuration}
        @type configuration: bsf.standards.Configuration
        @param section: Configuration file section
        @type section: str
        @return:
        @rtype:
        """

        super(SamToFastq, self).set_configuration(configuration=configuration, section=section)

        # Sub-class specific ...

        # Get the Picard tools Java Archive (JAR) class path directory.

        option = 'classpath_picard'
        if configuration.config_parser.has_option(section=section, option=option):
            self.classpath_picard = configuration.config_parser.get(section=section, option=option)

        option = 'include_non_pass_filter_reads'
        if configuration.config_parser.has_option(section=section, option=option):
            self.include_non_pass_filter_reads = configuration.config_parser.getboolean(section=section, option=option)

        return

    def _read_comparisons(self):

        self.samples.extend(self.collection.get_all_samples())

        return

    def run(self):
        """Run the C{bsf.analyses.picard.SamToFastq} C{bsf.Analysis} to convert a
        I{BAM} or I{SAM} file into I{FASTQ} files.

        This method changes the C{bsf.data.Collection} object of this C{bsf.Analysis} to update with FASTQ file paths.
        @return:
        @rtype:
        """

        super(SamToFastq, self).run()

        default = Default.get_global_default()

        # Get the Picard tools Java Archive (JAR) class path directory.

        if not self.classpath_picard:
            self.classpath_picard = default.classpath_picard

        self._read_comparisons()

        prune_sas_dependencies = list()

        # Picard SamToFastq

        stage_picard_stf = self.get_stage(name='picard_sam_to_fastq')

        for sample in self.samples:
            assert isinstance(sample, Sample)

            if self.debug > 0:
                print '{!r} Sample name: {}'.format(self, sample.name)
                print sample.trace(level=1)

            # bsf.data.Sample.get_all_paired_reads() returns a Python dict of
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
                        raise Exception('PairedReads object with reads1 but no reads2 object.', UserWarning)

                    reads = paired_reads.reads1
                    if reads.file_path.endswith('.bam'):
                        bam_file_path = reads.file_path
                        prefix_picard_stf = '_'.join((stage_picard_stf.name, replicate_key))

                        file_path_dict_picard_stf = {
                            'temporary_directory': '_'.join((prefix_picard_stf, 'temporary')),
                            'output_directory': os.path.join(self.project_directory, prefix_picard_stf),
                        }

                        # Get the SAM header of a BAM file to extract the read group (@RG), amongst other things.

                        # Open the BAM file, while not checking sequence (@SQ) entries.
                        # De-multiplexed, unaligned BAM files have no reference sequence dictionary.
                        # The check_sq option exists in the calignment code, yet, does not seem to be part of the
                        # function interface.

                        alignment_file = pysam.AlignmentFile(reads.file_path, 'rb', check_sq=False)

                        for read_group in alignment_file.header['RG']:
                            platform_unit = read_group['PU'].replace('#', '_')
                            read_group_list = ['@RG']
                            read_group_list.extend(map(lambda x: '{}:{}'.format(x, read_group[x]), read_group.keys()))
                            if read_group == alignment_file.header['RG'][0]:
                                # For the first read group, modify the PairedReads object in place.
                                paired_reads.read_group = '\\t'.join(read_group_list)
                                paired_reads.reads1.name = platform_unit + '_1'
                                paired_reads.reads1.file_path = os.path.join(
                                    file_path_dict_picard_stf['output_directory'],
                                    platform_unit + '_1.fastq')
                                paired_reads.reads2 = Reads(
                                    file_path=os.path.join(
                                        file_path_dict_picard_stf['output_directory'],
                                        platform_unit + '_2.fastq'),
                                    file_type=paired_reads.reads1.file_type,
                                    name=platform_unit + '_2',
                                    lane=paired_reads.reads1.lane,
                                    read=paired_reads.reads1.read,
                                    chunk=paired_reads.reads1.chunk,
                                    weak_reference_paired_reads=weakref.ref(paired_reads))
                            else:
                                # For further read groups, create new PairedReads objects.
                                reads1 = Reads(
                                    file_path=os.path.join(
                                        file_path_dict_picard_stf['output_directory'],
                                        platform_unit + '_1.fastq'),
                                    file_type=paired_reads.reads1.file_type,
                                    name=platform_unit + '_1',
                                    lane=paired_reads.reads1.lane,
                                    read='R1',
                                    chunk=paired_reads.reads1.chunk)
                                reads2 = Reads(
                                    file_path=os.path.join(
                                        file_path_dict_picard_stf['output_directory'],
                                        platform_unit + '_2.fastq'),
                                    file_type=paired_reads.reads2.file_type,
                                    name=platform_unit + '_2',
                                    lane=paired_reads.reads1.lane,
                                    read='R2',
                                    chunk=paired_reads.reads1.chunk)
                                new_paired_reads = PairedReads(
                                    reads1=reads1,
                                    reads2=reads2,
                                    read_group='\\t'.join(read_group_list))

                                reads1.weak_reference_paired_reads = weakref.ref(new_paired_reads)
                                reads2.weak_reference_paired_reads = weakref.ref(new_paired_reads)
                                sample.add_paired_reads(paired_reads=new_paired_reads)

                        alignment_file.close()

                        # Create a Runnable for running the Picard SamToFastq analysis.

                        runnable_picard_stf = self.add_runnable(
                            runnable=Runnable(
                                name=prefix_picard_stf,
                                code_module='bsf.runnables.generic',
                                working_directory=self.project_directory,
                                file_path_dict=file_path_dict_picard_stf))

                        # Create an Executable for running the Picard SamToFastq Runnable.

                        self.set_stage_runnable(stage=stage_picard_stf, runnable=runnable_picard_stf)

                        # Record the Executable.name for the prune_sas dependency.

                        prune_sas_dependencies.append(runnable_picard_stf.name)

                        # Create a new RunnableStepMakeDirectory in preparation of the Picard program.

                        runnable_picard_stf.add_runnable_step(
                            runnable_step=RunnableStepMakeDirectory(
                                name='mkdir',
                                directory_path=file_path_dict_picard_stf['output_directory']))

                        # Create a new RunnableStep for the Picard SamToFastq program.

                        runnable_step = runnable_picard_stf.add_runnable_step(
                            runnable_step=RunnableStepPicard(
                                name='picard_sam_to_fastq',
                                java_temporary_path=runnable_picard_stf.get_relative_temporary_directory_path,
                                java_heap_maximum='Xmx2G',
                                picard_classpath=self.classpath_picard,
                                picard_command='SamToFastq'))
                        assert isinstance(runnable_step, RunnableStepPicard)
                        runnable_step.add_picard_option(key='INPUT', value=bam_file_path)
                        runnable_step.add_picard_option(key='OUTPUT_PER_RG', value='true')
                        runnable_step.add_picard_option(
                            key='OUTPUT_DIR',
                            value=file_path_dict_picard_stf['output_directory'])
                        # RE_REVERSE
                        # INTERLEAVE
                        if self.include_non_pass_filter_reads:
                            runnable_step.add_picard_option(key='INCLUDE_NON_PF_READS', value='true')
                        else:
                            runnable_step.add_picard_option(key='INCLUDE_NON_PF_READS', value='false')
                        # CLIPPING_ATTRIBUTE
                        # CLIPPING_ACTION
                        # READ1_TRIM
                        # READ1_MAX_BASES_TO_WRITE
                        # READ2_TRIM
                        # READ2_MAX_BASES_TO_WRITE
                        # INCLUDE_NON_PRIMARY_ALIGNMENTS
                        runnable_step.add_picard_option(
                            key='TMP_DIR',
                            value=file_path_dict_picard_stf['temporary_directory'])
                        # VERBOSITY defaults to 'INFO'.
                        runnable_step.add_picard_option(key='VERBOSITY', value='WARNING')
                        # QUIET defaults to 'false'.
                        runnable_step.add_picard_option(key='QUIET', value='false')
                        # VALIDATION_STRINGENCY defaults to 'STRICT'.
                        runnable_step.add_picard_option(key='VALIDATION_STRINGENCY', value='STRICT')
                        # COMPRESSION_LEVEL defaults to '5'.
                        # MAX_RECORDS_IN_RAM defaults to '500000'.
                        # CREATE_INDEX defaults to 'false'.
                        # CREATE_MD5_FILE defaults to 'false'.
                        # OPTIONS_FILE

        # Convert the (modified) Collection object into a SampleAnnotationSheet object and write it to disk.

        annotation_sheet = self.collection.to_sas(
            file_path=os.path.join(
                self.project_directory,
                '_'.join((self.project_name, 'picard_sam_to_fastq_original.csv'))),
            name='_'.join((self.project_name, 'picard_sam_to_fastq')))

        annotation_sheet.to_file_path()

        # Create a Runnable for pruning the sample annotation sheet.

        prefix_prune_sas = '_'.join((stage_picard_stf.name, self.project_name))

        file_path_dict_prune_sas = {
            'temporary_directory': '_'.join((prefix_prune_sas, 'temporary')),
            'output_directory': prefix_prune_sas,
        }

        runnable_prune_sas = self.add_runnable(
            runnable=Runnable(
                name=prefix_prune_sas,
                code_module='bsf.runnables.picard_sam_to_fastq_sample_sheet',
                working_directory=self.project_directory,
                file_path_dict=file_path_dict_prune_sas))

        # Create an Executable for running the Runnable for pruning the sample annotation sheet.

        executable_prune_sas = self.set_stage_runnable(
            stage=stage_picard_stf,
            runnable=runnable_prune_sas)
        executable_prune_sas.dependencies.extend(prune_sas_dependencies)

        # Create a new RunnableStep.

        prune_sas = runnable_prune_sas.add_runnable_step(
            runnable_step=RunnableStep(
                name='prune_sample_annotation_sheet'))

        prune_sas.add_option_long(key='sas_path', value=annotation_sheet.file_path)

        return annotation_sheet
