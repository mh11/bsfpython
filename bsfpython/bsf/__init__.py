"""bsf

A package of classes and methods specific to the Biomedical Sequencing Facility (BSF).
Reference: http://www.biomedical-sequencing.at/
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


import datetime
import errno
import importlib
import os
import uuid
import warnings
from pickle import Pickler, Unpickler, HIGHEST_PROTOCOL
from stat import *

from bsf import defaults
from bsf.argument import *
from bsf.data import Collection, Sample
from bsf.process import Command, Executable, RunnableStep
from bsf.standards import Configuration, Default


class Analysis(object):
    """The C{Analysis} class represents a high-level analysis that may run one or more
    C{Executable} objects (programs).

    Attributes:
    @ivar configuration: C{Configuration}
    @type configuration: bsf.standards.Configuration
    @ivar debug: Debug level
    @type debug: int
    @ivar project_name: Project name (arbitrary)
    @type project_name: str
    @ivar genome_version: Genome version (e.g. hg19, mm10, GRCh37, GRCm38, ...)
    @type genome_version: str
    @ivar input_directory: Input directory
    @type input_directory: str | unicode
    @ivar output_directory: Output directory, user-specified including a genome version sub-directory
    @type output_directory: str | unicode
    @ivar project_directory: Project-specific directory
    @type project_directory: str | unicode
    @ivar genome_directory: Genome-specific directory
    @type genome_directory: str | unicode
    @ivar drms_list: Python C{list} of C{DRMS} objects
    @type drms_list: list[DRMS]
    @ivar runnable_dict: Python C{dict} of Python C{str} (C{Runnable.name}) key data and C{Runnable} value data
    @type runnable_dict: dict[Runnable.name, Runnable]
    @ivar collection: C{Collection}
    @type collection: Collection
    @ivar comparisons: Python C{dict} of comparisons
    @type comparisons: dict[str, any]
    @ivar samples: Python C{list} of C{Sample} objects
    @type samples: list[Sample]
    """

    @classmethod
    def from_config_file_path(cls, config_path):
        """Create a new C{Analysis} object from a UNIX-style configuration file path via the C{Configuration} class.

        @param config_path: UNIX-style configuration file path
        @type config_path: str | unicode
        @return: C{Analysis}
        @rtype: Analysis
        """

        return cls.from_configuration(configuration=Configuration.from_config_path(config_path=config_path))

    @classmethod
    def from_configuration(cls, configuration):
        """Create a new C{Analysis} object from a C{Configuration} object.

        @param configuration: C{Configuration}
        @type configuration: bsf.standards.Configuration
        @return: C{Analysis}
        @rtype: Analysis
        """

        assert isinstance(configuration, Configuration)

        # Set a minimal set of global defaults.

        default = Default.get_global_default()

        analysis = cls(configuration=configuration, e_mail=default.operator_e_mail)

        # A "module.class" configuration section specifies defaults for this Analysis or sub-class
        # i.e. "bsf.Analysis" or "bsf.analyses.*", respectively.

        analysis.set_configuration(
                configuration=analysis.configuration,
                section=Configuration.section_from_instance(instance=analysis))

        return analysis

    def __init__(self, configuration=None,
                 project_name=None, genome_version=None,
                 input_directory=None, output_directory=None,
                 project_directory=None, genome_directory=None,
                 sas_file=None, sas_prefix=None, e_mail=None, debug=0, drms_list=None,
                 runnable_dict=None, collection=None, comparisons=None, samples=None):
        """Initialise an C{Analysis} object.

        @param configuration: C{Configuration}
        @type configuration: bsf.standards.Configuration
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
        @param sas_file: Sample Annotation Sheet (SAS) file path
        @type sas_file: str | unicode
        @param sas_prefix: A prefix to columns in a Sample Annotation Sheet
            (e.g. Control Sample, Treatment Sample, ...)
        @type sas_prefix: str
        @param e_mail: e-Mail address for a UCSC Genome Browser Track Hub
        @type e_mail: str
        @param debug: Integer debugging level
        @type debug: int
        @param drms_list: Python C{list} of C{DRMS} objects
        @type drms_list: list[DRMS]
        @param runnable_dict: Python C{dict} of Python C{str} (C{Runnable.name}) and C{Runnable} value data
        @type runnable_dict: dict[Runnable.name, Runnable]
        @param collection: C{Collection}
        @type collection: Collection
        @param comparisons: Python C{dict} of Analysis-specific objects
            (i.e. Python tuple for RNA-Seq and ChIPSeqComparison for ChIPSeq)
        @type comparisons: dict[str, Any]
        @param samples: Python C{list} of C{Sample} objects
        @type samples: list[Sample]
        @return:
        @rtype:
        """

        super(Analysis, self).__init__()

        if configuration is None:
            self.configuration = Configuration()
        else:
            assert isinstance(configuration, Configuration)
            self.configuration = configuration

        if project_name is None:
            self.project_name = str()
        else:
            self.project_name = project_name

        if genome_version is None:
            self.genome_version = str()
        else:
            self.genome_version = genome_version

        if input_directory is None:
            self.input_directory = str()
        else:
            self.input_directory = input_directory

        if output_directory is None:
            self.output_directory = str()
        else:
            self.output_directory = output_directory

        if project_directory is None:
            self.project_directory = str()
        else:
            self.project_directory = project_directory

        if genome_directory is None:
            self.genome_directory = str()
        else:
            self.genome_directory = genome_directory

        if sas_file is None:
            self.sas_file = str()
        else:
            self.sas_file = sas_file

        if sas_prefix is None:
            self.sas_prefix = str()
        else:
            self.sas_prefix = sas_prefix

        if e_mail is None:
            self.e_mail = str()
        else:
            self.e_mail = e_mail

        if debug is None:
            self.debug = int(x=0)
        else:
            assert isinstance(debug, int)
            self.debug = debug

        if drms_list is None:
            self.drms_list = list()
        else:
            self.drms_list = drms_list

        if runnable_dict is None:
            self.runnable_dict = dict()
        else:
            self.runnable_dict = runnable_dict

        if collection is None:
            self.collection = Collection()
        else:
            assert isinstance(collection, Collection)
            self.collection = collection

        if comparisons is None:
            self.comparisons = dict()
        else:
            self.comparisons = comparisons

        if samples is None:
            self.samples = list()
        else:
            self.samples = samples

        return

    def trace(self, level):
        """Trace an C{Analysis} object.

        @param level: Indentation level
        @type level: int
        @return: Trace information
        @rtype: str
        """

        indent = '  ' * level
        output = str()
        output += '{}{!r}\n'.format(indent, self)
        output += '{}  project_name: {!r}\n'.format(indent, self.project_name)
        output += '{}  genome_version: {!r}\n'.format(indent, self.genome_version)
        output += '{}  input_directory: {!r}\n'.format(indent, self.input_directory)
        output += '{}  output_directory: {!r}\n'.format(indent, self.output_directory)
        output += '{}  genome_directory: {!r}\n'.format(indent, self.genome_directory)
        output += '{}  sas_file: {!r}\n'.format(indent, self.sas_file)
        output += '{}  sas_prefix: {!r}\n'.format(indent, self.sas_prefix)
        output += '{}  e_mail: {!r}\n'.format(indent, self.e_mail)
        output += '{}  debug: {!r}\n'.format(indent, self.debug)
        output += '{}  drms_list: {!r}\n'.format(indent, self.drms_list)
        output += '{}  runnable_dict: {!r}\n'.format(indent, self.runnable_dict)
        output += '{}  collection: {!r}\n'.format(indent, self.collection)
        output += '{}  comparisons: {!r}\n'.format(indent, self.comparisons)
        output += '{}  samples: {!r}\n'.format(indent, self.samples)

        output += '{}  Python dict of Runnable objects:\n'.format(indent)
        keys = self.runnable_dict.keys()
        keys.sort(cmp=lambda x, y: cmp(x, y))
        for key in keys:
            assert isinstance(key, str)
            output += '{}    Key: {!r} Runnable: {!r}\n'.format(indent, key, self.runnable_dict[key])
            runnable = self.runnable_dict[key]
            assert isinstance(runnable, Runnable)
            output += runnable.trace(level=level + 2)

        output += '{}  Python List of Sample objects:\n'.format(indent)
        for sample in self.samples:
            assert isinstance(sample, Sample)
            output += '{}    Sample name: {!r} file_path: {!r}\n'.format(indent, sample.name, sample.file_path)

        if self.collection:
            output += self.collection.trace(level + 1)

        return output

    def add_drms(self, drms):
        """Convenience method to facilitate initialising, adding and returning a C{DRMS} object.

        @param drms: C{DRMS}
        @type drms: DRMS
        @return: C{DRMS}
        @rtype: DRMS
        """
        assert isinstance(drms, DRMS)

        if drms not in self.drms_list:
            self.drms_list.append(drms)

        return drms

    def add_runnable(self, runnable):
        """Convenience method to facilitate initialising, adding and returning a C{Runnable}.

        @param runnable: C{Runnable}
        @type runnable: Runnable
        @return: C{Runnable}
        @rtype: Runnable
        @raise Exception: The C{Runnable.name} already exists in the C{Analysis}
        """
        assert isinstance(runnable, Runnable)

        if runnable.name in self.runnable_dict:
            raise Exception("A Runnable object with name {!r} already exists in Analysis {!r}".
                            format(runnable.name, self.project_name))
        else:
            self.runnable_dict[runnable.name] = runnable

        return runnable

    def add_sample(self, sample):
        """Add a C{Sample} object to the Python C{list} of C{Sample} objects if it does not already exist.

        The check is based on the Python 'in' comparison operator and in lack of a specific
        __cmp__ method, relies on object identity (i.e. address).
        @param sample: C{Sample}
        @type sample: Sample
        @return:
        @rtype:
        """
        assert isinstance(sample, Sample)

        if sample not in self.samples:
            self.samples.append(sample)

        return

    def set_configuration(self, configuration, section):
        """Set instance variables of an C{Analysis} object via a section of a C{Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: Configuration
        @type configuration: bsf.standards.Configuration
        @param section: Configuration file section
        @type section: str
        @raise Exception: The specified section does not exist
        @return:
        @rtype:
        """
        assert isinstance(configuration, Configuration)
        assert isinstance(section, str)

        if not configuration.config_parser.has_section(section=section):
            raise Exception(
                    'Section {!r} not defined in Configuration file {!r}.'.format(
                            section,
                            configuration.config_path))

        # The configuration section is available.

        option = 'debug'
        if configuration.config_parser.has_option(section=section, option=option):
            self.debug = configuration.config_parser.getint(section=section, option=option)

        option = 'project_name'
        if configuration.config_parser.has_option(section=section, option=option):
            self.project_name = configuration.config_parser.get(section=section, option=option)

        option = 'input_directory'
        if configuration.config_parser.has_option(section=section, option=option):
            self.input_directory = configuration.config_parser.get(section=section, option=option)

        option = 'output_directory'
        if configuration.config_parser.has_option(section=section, option=option):
            self.output_directory = configuration.config_parser.get(section=section, option=option)

        option = 'genome_version'
        if configuration.config_parser.has_option(section=section, option=option):
            self.genome_version = configuration.config_parser.get(section=section, option=option)

        option = 'sas_file'
        if configuration.config_parser.has_option(section=section, option=option):
            self.sas_file = configuration.config_parser.get(section=section, option=option)

        option = 'sas_prefix'
        if configuration.config_parser.has_option(section=section, option=option):
            self.sas_prefix = configuration.config_parser.get(section=section, option=option)

        option = 'e_mail'
        if configuration.config_parser.has_option(section=section, option=option):
            self.e_mail = configuration.config_parser.get(section=section, option=option)

        return

    def set_command_configuration(self, command):
        """Set default C{Arguments} for a C{Command} or sub-class object in the context of this C{Analysis} object.

        @param command: C{Command}
        @type command: bsf.process.Command
        """
        assert isinstance(command, Command)

        section = Configuration.section_from_instance(instance=command)

        # For plain Executable objects append the value of the
        # Executable.program to make this more meaningful.

        if section == 'bsf.process.Executable':
            section += '.'
            section += command.program

        if self.debug > 1:
            print 'Command configuration section: {!r}.'.format(section)

        command.set_configuration(configuration=self.configuration, section=section)

    def set_drms_runnable(self, drms, runnable):
        """Create an C{Executable} to submit a C{Runnable} into a C{DRMS}.

        In case C{Runnable.get_relative_status_path} exists already, C{Executable.submit} will be set to C{False}.
        @param drms: C{DRMS}
        @type drms: DRMS
        @param runnable: C{Runnable}
        @type runnable: Runnable
        @return: C{Executable}
        @rtype: bsf.process.Executable
        @raise Exception: A C{Runnable.name} does not exist in C{Analysis}
        """
        assert isinstance(drms, DRMS)
        assert isinstance(runnable, Runnable)

        if drms not in self.drms_list:
            raise Exception("A DRMS object with name {!r} does not exist in the Analysis object with name {!r}.".
                            format(drms.name, self.project_name))

        if runnable.name not in self.runnable_dict:
            raise Exception("A Runnable object with name {!r} does not exist in the Analysis object with name {!r}.".
                            format(runnable.name, self.project_name))

        executable = Executable(name=runnable.name, program=Runnable.runner_script)
        # TODO: Read configuration files for RunnableStep objects rather than Runnable objects.
        # Since bsf.Runnable.code_module objects such as 'bsf.runnables.generic' can be very generic,
        # it makes no sense to read standard configuration options from a Configuration object.
        # executable.set_configuration(configuration=analysis.configuration, section=runnable.code_module)
        # It would be better to read standard configuration options for RunnableStep objects.
        executable.add_option_long(key='pickler-path', value=runnable.pickler_path)

        # Only submit the Executable if the status file does not exist already.
        if os.path.exists(runnable.get_absolute_status_path):
            executable.submit = False

        drms.add_executable(executable=executable)

        return executable

    def run(self):
        """Run the C{Analysis}.

        @raise Exception: An C{Analysis.project_name} has not been defined
        @return:
        @rtype:
        """

        if not self.project_name:
            raise Exception('An Analysis project_name has not been defined.')

        # Some analyses such as FastQC do not require a genome_version,
        # nor a genome_version-specific output directory.
        # Also, add the e-mail address for UCSC track hubs into the genome subclass.

        # Expand an eventual user part i.e. on UNIX ~ or ~user and
        # expand any environment variables i.e. on UNIX ${NAME} or $NAME
        # Check if an absolute path has been provided, if not,
        # automatically prepend standard directory paths.

        self.input_directory = Default.get_absolute_path(
                file_path=self.input_directory,
                default_path=Default.absolute_samples())

        self.output_directory = Default.get_absolute_path(
                file_path=self.output_directory,
                default_path=Default.absolute_projects())

        # As a safety measure, to prevent creation of rogue directory paths, the output_directory has to exist.

        if not os.path.isdir(self.output_directory):
            raise Exception('The Analysis output_directory {!r} does not exist.'.format(self.output_directory))

        # Define project_directory and genome_directory instance variables.
        # If a genome_version option is present, append
        # it to the project_directory instance variable.
        # This allows analyses run against more than one directory and
        # simplifies UCSC Genome Browser track hub creation.

        self.project_directory = os.path.join(self.output_directory, self.project_name)

        if self.genome_version:
            self.genome_directory = os.path.join(self.project_directory, self.genome_version)
        else:
            self.genome_directory = self.project_directory

        if not os.path.isdir(self.genome_directory):
            try:
                os.makedirs(self.genome_directory)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise

        if self.sas_file:
            # Populate a Collection from a SampleAnnotationSheet.
            self.sas_file = os.path.expanduser(path=self.sas_file)
            self.sas_file = os.path.expandvars(path=self.sas_file)

            if not os.path.isabs(self.sas_file) and not os.path.exists(self.sas_file):
                self.sas_file = os.path.join(self.project_directory, self.sas_file)

            self.collection = Collection.from_sas_path(
                    file_path=self.input_directory,
                    file_type='Automatic',
                    name=self.project_name,
                    sas_path=self.sas_file,
                    sas_prefix=self.sas_prefix)

            if self.debug > 1:
                print '{!r} Collection name: {!r}'.format(self, self.collection.name)
                print self.collection.trace(1)
        else:
            # Create an empty Collection.
            self.collection = Collection()

        return

    def report(self):
        """Create an C{Analysis} report.

        The method must be implemented in a sub-class.
        @return:
        @rtype:
        """

        warnings.warn(
                "The 'report' method must be implemented in the sub-class.",
                UserWarning)

        return

    def create_project_genome_directory(self):
        """Check and create an C{Analysis.project_directory} or C{Analysis.genome_directory} if necessary.

        @return:
        @rtype:
        @raise Exception: Output (genome) directory does not exist
        """

        if not os.path.isdir(self.genome_directory):
            answer = raw_input(
                    "Output (genome) directory {!r} does not exist.\n"
                    'Create? [Y/n] '.format(self.genome_directory))

            if not answer or answer == 'Y' or answer == 'y':
                # In principle, a race condition could occur as the directory
                # could have been created after its existence has been checked.
                try:
                    os.makedirs(self.genome_directory)
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
            else:
                raise Exception(
                        'Output (genome) directory {!r} does not exist.'.format(self.genome_directory))

        return

    def create_public_project_link(self, sub_directory=None):
        """Create a symbolic link from the web directory to the project directory if not already there.

        The link will be placed in the sub directory and contain
        the project name followed by a 128 bit hexadecimal UUID string.
        @param sub_directory: C{Analysis}-specific directory
        @type sub_directory: str
        @return: Symbolic link to the project directory
        @rtype: str
        @raise Exception: Public HTML path does not exist
        """

        # The html_path consists of the absolute public_html directory and
        # the analysis-specific sub-directory.

        html_path = Default.absolute_public_html()

        if sub_directory:
            html_path = os.path.join(html_path, sub_directory)

        # As a safety measure, to prevent creation of rogue directory paths, the html_path directory has to exist.

        if not os.path.isdir(html_path):
            raise Exception(
                    "The public HTML path {!r} does not exist.\n"
                    "Please check the optional sub-directory name {!r}.".format(html_path, sub_directory))

        # The link_name consists of the absolute public_html directory,
        # the analysis-specific sub-directory, the project name and a 128 bit hexadecimal UUID string.

        link_name = os.path.join(html_path, '_'.join((self.project_name, uuid.uuid4().hex)))

        # While checking for already existing symbolic links,
        # the path_name holds the complete path for each link in the sub-directory.

        path_name = str()

        # The link_final holds the final symbolic link. It can be the link_name assembled above or
        # point to an already existing one.

        link_final = link_name

        link_exists = False

        for file_name in os.listdir(html_path):
            path_name = os.path.join(html_path, file_name)
            mode = os.lstat(path_name).st_mode
            if S_ISLNK(mode):
                target_name = os.readlink(path_name)
                if not os.path.isabs(target_name):
                    target_name = os.path.join(html_path, target_name)
                if not os.path.exists(path=target_name):
                    # Both paths for os.path.samefile have to exist.
                    # Check for dangling symbolic links.
                    warnings.warn(
                            'Dangling symbolic link {!r} to {!r}'.format(path_name, target_name),
                            UserWarning)
                    continue
                if os.path.samefile(target_name, self.project_directory):
                    link_exists = True
                    link_final = path_name  # Reset link_final to the already existing path_name.
                    break

        if link_exists:
            # Ask the user to re-create the symbolic link.
            answer = raw_input(
                    "Public HTML link {!r} to {!r} does exist.\n"
                    "Re-create? [y/N] ".format(path_name, self.project_directory))

            if not answer or answer == 'N' or answer == 'n':
                print 'Public HTML link {!r} to {!r} not reset.'. \
                    format(path_name, self.project_directory)
            else:
                try:
                    os.remove(path_name)
                except OSError as exception:
                    # In principle, a race condition could occur as the directory
                    # could have been created after its existence has been checked.
                    if exception.errno != errno.ENOENT:
                        raise
                try:
                    os.symlink(os.path.relpath(self.project_directory, html_path), link_name)
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
        else:
            # Ask the user to create a symbolic link.
            answer = raw_input(
                    'Public HTML link {!r} to {!r} does not exist.\n'
                    'Create? [Y/n] '.format(link_name, self.project_directory))

            if not answer or answer == 'Y' or answer == 'y':
                # In principle, a race condition could occur as the directory
                # could have been created after its existence has been checked.
                try:
                    os.symlink(os.path.relpath(self.project_directory, html_path), link_name)
                except OSError as exception:
                    if exception.errno != errno.EEXIST:
                        raise
            else:
                print 'Public HTML link {!r} to {!r} not set.'. \
                    format(link_name, self.project_directory)

        return link_final

    def ucsc_hub_write_hub(self, prefix=None):
        """Write a UCSC Track Hub I{hub.txt} file into the C{Analysis.project_directory},
        above the C{Analysis.genome_directory}.

        @param prefix: A hub prefix (e.g. chipseq, rnaseq, ...)
        @type prefix: str
        @return:
        @rtype:
        """

        output = str()

        if prefix is None or not prefix:
            file_name = 'hub.txt'
            output += 'hub {}\n'.format(self.project_name)
            output += 'shortLabel {}\n'.format(self.project_name)
            output += 'longLabel Project {}\n'.format(self.project_name)
            output += 'genomesFile genomes.txt\n'
        else:
            file_name = '{}_hub.txt'.format(prefix)
            output += 'hub {}_{}\n'.format(self.project_name, prefix)
            output += 'shortLabel {}_{}\n'.format(self.project_name, prefix)
            output += 'longLabel Project {}_{}\n'.format(self.project_name, prefix)
            output += 'genomesFile {}_genomes.txt\n'.format(prefix)

        output += 'email {}\n'.format(self.e_mail)

        # The [prefix_]hub.txt goes into the project directory above the genome directory.
        file_path = os.path.join(self.project_directory, file_name)

        file_handle = open(name=file_path, mode='w')
        file_handle.write(output)
        file_handle.close()

        return

    def ucsc_hub_write_genomes(self, prefix=None):
        """Write a UCSC Track Hub I{genomes.txt} file into the C{Analysis.project_directory},
        above the C{Analysis.genome_directory}.

        @param prefix: A hub prefix (e.g. chipseq, rnaseq, ...)
        @type prefix: str
        @return:
        @rtype:
        """

        output = str()

        output += 'genome {}\n'.format(self.genome_version)
        if prefix is None or not prefix:
            file_name = 'genomes.txt'
            output += 'trackDb {}/trackDB.txt\n'.format(self.genome_version)
        else:
            file_name = '{}_genomes.txt'.format(prefix)
            output += 'trackDb {}/{}_trackDB.txt\n'.format(self.genome_version, prefix)

        # The [prefix_]genomes.txt goes into the project directory above the genome directory.
        file_path = os.path.join(self.project_directory, file_name)

        file_handle = open(name=file_path, mode='w')
        file_handle.write(output)
        file_handle.close()

        return

    def ucsc_hub_write_tracks(self, output, prefix=None):
        """Write a UCSC Track Hub I{trackDB.txt} file into the C{Analysis.genome_directory}.

        @param output: Content
        @type output: str
        @param prefix: A hub prefix (e.g. chipseq, rnaseq, ...)
        @type prefix: str
        @return:
        @rtype:
        """

        if prefix is None or not prefix:
            file_name = 'trackDB.txt'
        else:
            file_name = '{}_trackDB.txt'.format(prefix)

        # The [prefix_]trackDB.txt goes into the genome directory under the project directory.
        file_path = os.path.join(self.genome_directory, file_name)

        file_handle = open(name=file_path, mode='w')
        file_handle.write(output)
        file_handle.close()

        return

    def submit(self, drms_name=None):
        """Submit each C{DRMS} object and pickle each C{Runnable} object.

        @param drms_name: Only submit C{Executable} objects linked to C{DRMS.name}
        @type drms_name: str
        @return:
        @rtype:
        """

        # Pickle all Runnable objects.

        for key in self.runnable_dict.keys():
            assert isinstance(key, str)
            self.runnable_dict[key].to_pickler_path()

        # Submit all Executable objects of all Distributed Resource Management System objects.

        submit = 0

        for drms in self.drms_list:
            assert isinstance(drms, DRMS)
            if drms_name:
                if drms_name == drms.name:
                    submit += 1
                else:
                    continue
            drms.submit(debug=self.debug)

            if self.debug:
                print repr(drms)
                print drms.trace(1)

        if drms_name:
            if drms_name == 'report':
                self.report()
            elif not submit:
                name_list = [drms.name for drms in self.drms_list]
                name_list.append('report')
                print 'Valid Analysis DRMS names are: {!r}'.format(name_list)

        return


class DRMS(object):
    """The I{Distributed Resource Management System} (C{DRMS}) class represents a
    I{Distributed Resource Management System} or batch job scheduler.

    Attributes:
    @ivar name: Name
    @type name: str
    @ivar working_directory: Working directory path
    @type working_directory: str
    @ivar implementation: Implementation (e.g. I{sge}, I{slurm}, ...)
    @type implementation: str
    @ivar memory_free_mem: Memory limit (free)
    @type memory_free_mem: str
    @ivar memory_limit_hard: Memory limit (hard)
    @type memory_limit_hard: str
    @ivar memory_limit_soft: Memory limit (soft)
    @type memory_limit_soft: str
    @ivar parallel_environment: Parallel environment
    @type parallel_environment: str
    @ivar queue: Queue
    @type queue: str
    @ivar threads: Number of threads
    @type threads: int
    @ivar hold: Hold on job scheduling
    @type hold: str
    @ivar is_script: C{Executable} objects represent shell scripts,
        or alternatively binary programs
    @type is_script: bool
    @ivar executables: Python C{list} of C{Executable} objects
    @type executables: list[bsf.process.Executable]
    """

    @classmethod
    def from_analysis(cls, name, working_directory, analysis):
        """Create a C{DRMS} object from an C{Analysis} object.

        @param name: Name
        @type name: str
        @param working_directory: Working directory
        @type working_directory: str
        @param analysis: C{Analysis}
        @type analysis: Analysis
        @return: C{DRMS} object
        @rtype: DRMS
        """

        assert isinstance(analysis, Analysis)

        drms = cls(name=name, working_directory=working_directory)

        # Set a minimal set of global defaults.

        drms.set_default(default=Default.get_global_default())

        # A "bsf.DRMS" section specifies defaults for all DRMS objects of an Analysis.

        section = Configuration.section_from_instance(instance=drms)
        drms.set_configuration(configuration=analysis.configuration, section=section)

        if analysis.debug > 1:
            print 'DRMS configuration section: {!r}.'.format(section)

        # A "bsf.Analysis.DRMS" or "bsf.analyses.*.DRMS" pseudo-class section specifies
        # Analysis-specific or sub-class-specific options for the DRMS, respectively.

        section = '.'.join((Configuration.section_from_instance(instance=analysis), 'DRMS'))
        drms.set_configuration(configuration=analysis.configuration, section=section)

        if analysis.debug > 1:
            print 'DRMS configuration section: {!r}.'.format(section)

        # A "bsf.Analysis.DRMS.name" or "bsf.analyses.*.DRMS.name" section specifies defaults
        # for a particular DRMS object of an Analysis or sub-class, respectively.

        section = '.'.join((Configuration.section_from_instance(instance=analysis), 'DRMS', drms.name))
        drms.set_configuration(configuration=analysis.configuration, section=section)

        if analysis.debug > 1:
            print 'DRMS configuration section: {!r}.'.format(section)

        return drms

    @classmethod
    def from_configuration(cls, name, work_directory, configuration, section):
        """Create a C{DRMS} object from a C{Configuration} object.

        @param name: Name
        @type name: str
        @param work_directory: Work directory
        @type work_directory: str
        @param configuration: C{Configuration} object
        @type configuration: bsf.standards.Configuration
        @param section: Configuration section string
        @type section: str
        @return: C{DRMS} object
        @rtype: DRMS
        """

        assert isinstance(configuration, Configuration)

        drms = cls(name=name, work_directory=work_directory)

        # Set a minimal set of global defaults before setting the Configuration.

        drms.set_default(default=Default.get_global_default())
        drms.set_configuration(configuration=configuration, section=section)

        return drms

    def __init__(self, name, working_directory, implementation=None, memory_free_mem=None, memory_free_swap=None,
                 memory_free_virtual=None, memory_limit_hard=None, memory_limit_soft=None, time_limit=None,
                 parallel_environment=None, queue=None, threads=1, hold=None, is_script=False, executables=None):
        """Initialise a C{DRMS} object.

        @param name: Name
        @type name: str
        @param working_directory: Working directory
        @type working_directory: str
        @param implementation: Implementation (e.g. I{sge}, I{slurm}, ...)
        @type implementation: str
        @param memory_free_mem: Memory limit (free physical)
        @type memory_free_mem: str
        @param memory_free_swap: Memory limit (free swap)
        @type memory_free_swap: str
        @param memory_free_virtual: Memory limit (free virtual)
        @type memory_free_virtual: str
        @param memory_limit_hard: Memory limit (hard)
        @type memory_limit_hard: str
        @param memory_limit_soft: Memory limit (soft)
        @type memory_limit_soft: str
        @param time_limit: Time limit
        @type time_limit: str
        @param parallel_environment: Parallel environment
        @type parallel_environment: str
        @param queue: Queue
        @type queue: str
        @param threads: Number of threads
        @type threads: int
        @param hold: Hold on job scheduling
        @type hold: str
        @param is_script: C{Executable} objects represent shell scripts,
            or alternatively binary programs
        @type is_script: bool
        @param executables: Python C{list} of C{Executable} objects
        @type executables: list[bsf.process.Executable]
        @return:
        @rtype:
        """

        super(DRMS, self).__init__()

        if name is None:
            self.name = str()
        else:
            self.name = name

        if working_directory is None:
            self.working_directory = str()
        else:
            self.working_directory = working_directory

        if implementation is None:
            self.implementation = str()
        else:
            self.implementation = implementation

        if memory_free_mem is None:
            self.memory_free_mem = str()
        else:
            self.memory_free_mem = memory_free_mem

        if memory_free_swap is None:
            self.memory_free_swap = str()
        else:
            self.memory_free_swap = memory_free_swap

        if memory_free_virtual is None:
            self.memory_free_virtual = str()
        else:
            self.memory_free_virtual = memory_free_virtual

        if memory_limit_hard is None:
            self.memory_limit_hard = str()
        else:
            self.memory_limit_hard = memory_limit_hard

        if memory_limit_soft is None:
            self.memory_limit_soft = str()
        else:
            self.memory_limit_soft = memory_limit_soft

        if time_limit is None:
            self.time_limit = str()
        else:
            self.time_limit = time_limit

        if parallel_environment is None:
            self.parallel_environment = str()
        else:
            self.parallel_environment = parallel_environment

        if queue is None:
            self.queue = str()
        else:
            self.queue = queue

        if threads is None:
            self.threads = int(x=1)
        else:
            assert isinstance(threads, int)
            self.threads = threads

        if hold is None:
            self.hold = str()
        else:
            self.hold = hold

        if is_script is None:
            self.is_script = False
        else:
            assert isinstance(is_script, bool)
            self.is_script = is_script

        if executables is None:
            self.executables = list()
        else:
            self.executables = executables

        return

    def trace(self, level):
        """Trace a C{DRMS} object.

        @param level: Indentation level
        @type level: int
        @return: Trace information
        @rtype: str
        """

        indent = '  ' * level
        output = str()
        output += '{}{!r}\n'.format(indent, self)
        output += '{}  name:                 {!r}\n'. \
            format(indent, self.name)
        output += '{}  working_directory:       {!r}\n'. \
            format(indent, self.working_directory)
        output += '{}  implementation:       {!r}\n'. \
            format(indent, self.implementation)
        output += '{}  memory_free_mem:      {!r}\n'. \
            format(indent, self.memory_free_mem)
        output += '{}  memory_free_swap:     {!r}\n'. \
            format(indent, self.memory_free_swap)
        output += '{}  memory_free_virtual:  {!r}\n'. \
            format(indent, self.memory_free_virtual)
        output += '{}  memory_limit_hard:    {!r}\n'. \
            format(indent, self.memory_limit_hard)
        output += '{}  memory_limit_soft:    {!r}\n'. \
            format(indent, self.memory_limit_soft)
        output += '{}  time_limit:           {!r}\n'. \
            format(indent, self.time_limit)
        output += '{}  queue:                {!r}\n'. \
            format(indent, self.queue)
        output += '{}  parallel_environment: {!r}\n'. \
            format(indent, self.parallel_environment)
        output += '{}  threads:              {!r}\n'. \
            format(indent, self.threads)
        output += '{}  hold:                 {!r}\n'. \
            format(indent, self.hold)
        output += '{}  is_script:            {!r}\n'. \
            format(indent, self.is_script)

        output += '{}  executables:\n'.format(indent)

        for executable in self.executables:
            assert isinstance(executable, Executable)
            output += executable.trace(level=level + 2)

        return output

    def set_configuration(self, configuration, section):
        """Set instance variables of a C{DRMS} object via a section of a C{Configuration} object.

        Instance variables without a configuration option remain unchanged.
        @param configuration: C{Configuration}
        @type configuration: bsf.standards.Configuration
        @param section: Configuration file section
        @type section: str
        @return:
        @rtype:
        """

        assert isinstance(configuration, Configuration)
        assert isinstance(section, str)

        if not configuration.config_parser.has_section(section=section):
            raise Exception(
                    'Section {!r} not defined in Configuration file {!r}.'.format(
                            section,
                            configuration.config_path))

        # The configuration section is available.

        option = 'hold'
        if configuration.config_parser.has_option(section=section, option=option):
            self.hold = configuration.config_parser.get(section=section, option=option)

        option = 'implementation'
        if configuration.config_parser.has_option(section=section, option=option):
            self.implementation = configuration.config_parser.get(section=section, option=option)

        option = 'is_script'
        if configuration.config_parser.has_option(section=section, option=option):
            self.is_script = configuration.config_parser.getboolean(section=section, option=option)

        option = 'memory_free_mem'
        if configuration.config_parser.has_option(section=section, option=option):
            self.memory_free_mem = configuration.config_parser.get(section=section, option=option)

        option = 'memory_free_swap'
        if configuration.config_parser.has_option(section=section, option=option):
            self.memory_free_swap = configuration.config_parser.get(section=section, option=option)

        option = 'memory_free_virtual'
        if configuration.config_parser.has_option(section=section, option=option):
            self.memory_free_virtual = configuration.config_parser.get(section=section, option=option)

        option = 'memory_hard'
        if configuration.config_parser.has_option(section=section, option=option):
            self.memory_limit_hard = configuration.config_parser.get(section=section, option=option)

        option = 'memory_soft'
        if configuration.config_parser.has_option(section=section, option=option):
            self.memory_limit_soft = configuration.config_parser.get(section=section, option=option)

        option = 'time_limit'
        if configuration.config_parser.has_option(section=section, option=option):
            self.time_limit = configuration.config_parser.get(section=section, option=option)

        option = 'parallel_environment'
        if configuration.config_parser.has_option(section=section, option=option):
            self.parallel_environment = configuration.config_parser.get(section=section, option=option)

        option = 'queue'
        if configuration.config_parser.has_option(section=section, option=option):
            self.queue = configuration.config_parser.get(section=section, option=option)

        option = 'threads'
        if configuration.config_parser.has_option(section=section, option=option):
            self.threads = configuration.config_parser.get(section=section, option=option)

        return

    def set_default(self, default):
        """Set instance variables of a C{DRMS} object via a C{Default} object.

        @param default: C{Default} object
        @type default: bsf.standards.Default
        @return:
        @rtype:
        """

        assert isinstance(default, Default)

        self.implementation = default.drms_implementation
        # is_script
        # memory_free_mem
        # memory_free_swap
        # memory_free_virtual
        self.memory_limit_hard = default.drms_memory_limit_hard
        self.memory_limit_soft = default.drms_memory_limit_soft
        self.time_limit = default.drms_time_limit
        self.parallel_environment = default.drms_parallel_environment
        self.queue = default.drms_queue
        # threads

        return

    def add_executable(self, executable):
        """Convenience method to facilitate initialising, adding and returning an C{Executable}.

        @param executable: C{Executable}
        @type executable: bsf.process.Executable
        @return: C{Executable}
        @rtype: bsf.process.Executable
        """

        assert isinstance(executable, Executable)

        self.executables.append(executable)

        return executable

    def submit(self, debug=0):
        """Submit a command line for each C{Executable} object.

        @param debug: Debug level
        @type debug: int
        @return:
        @rtype:
        """

        # Dynamically import the module specific for the configured DRMS implementation.

        module = importlib.import_module('.'.join((__name__, 'drms', self.implementation)))

        module.submit(drms=self, debug=debug)

        return


class Runnable(object):
    """The C{Runnable} class holds all information to run one or more C{Executable} objects through the
    I{Runner} script. It can be thought of a script that executes runnable steps.

    Attributes:
    @cvar runner_script: Name of the I{Runner} script
    @type runner_script: str | unicode
    @ivar name: Name
    @type name: str
    @ivar code_module: The name of a module, usually in C{bsf.runnables} that implements the logic required to run
        C{Executable} objects via the I{Runner} script.
    @type code_module: str
    @ivar executable_dict: Python C{dict} of Python C{str} (C{Executable.name}) key data and C{Executable} value data
    @type executable_dict: dict[bsf.process.Executable.name, bsf.process.Executable]
    @ivar file_path_dict: Python C{dict} of Python C{str} (name) key data and Python C{str} (file_path) value data
    @type file_path_dict: dict[str, str | unicode]
    @ivar runnable_step_list: Python C{list} of C{RunnableStep} objects
    @type runnable_step_list: list[bsf.process.RunnableStep]
    @ivar working_directory: Working directory to write C{pickle.Pickler} files
    @type working_directory: str | unicode
    @ivar debug: Debug level
    @type debug: int
    """

    runner_script = 'bsf_runner.py'

    def __init__(self, name, code_module, working_directory, file_path_dict=None, executable_dict=None,
                 runnable_step_list=None, debug=0):
        """Initialise a C{Runnable} object.

        @param name: Name
        @type name: str
        @param code_module: The name of a module, usually in C{bsf.runnables} that implements the logic required to run
            C{Executable} objects via the I{Runner} script
        @type code_module: str
        @param working_directory: Working directory for writing a Python C{pickle.Pickler} file
        @type working_directory: str | unicode
        @param file_path_dict: Python C{dict} of Python C{str} (name) key data and
            Python C{str} (file_path) value data
        @type file_path_dict: dict[bsf.process.Executable.name, bsf.process.Executable]
        @param executable_dict: Python C{dict} of Python C{str} (C{Executable.name}) key data and
            C{Executable} value data
        @type executable_dict: dict[str, str | unicode]
        @param runnable_step_list: Python C{list} of C{RunnableStep} objects
        @type runnable_step_list: list[bsf.process.RunnableStep]
        @param debug: Integer debugging level
        @type debug: int
        @return:
        @rtype:
        """

        super(Runnable, self).__init__()

        self.name = name  # Can be None.
        self.code_module = code_module  # Can be None.
        self.working_directory = working_directory  # Can be None.

        if file_path_dict is None:
            self.file_path_dict = dict()
        else:
            self.file_path_dict = file_path_dict

        if executable_dict is None:
            self.executable_dict = dict()
        else:
            self.executable_dict = executable_dict

        if runnable_step_list is None:
            self.runnable_step_list = list()
        else:
            self.runnable_step_list = runnable_step_list

        if debug is None:
            self.debug = int(x=0)
        else:
            assert isinstance(debug, int)
            self.debug = debug

        return

    def trace(self, level=1):
        """Trace a C{Runnable} object.

        @param level: Indentation level
        @type level: int
        @return: Trace information
        @rtype: str
        """

        indent = '  ' * level
        output = str()
        output += '{}{!r}\n'.format(indent, self)
        output += '{}  name: {!r}\n'.format(indent, self.name)
        output += '{}  code_module: {!r}\n'.format(indent, self.code_module)
        output += '{}  working_directory: {!r}\n'.format(indent, self.working_directory)
        output += '{}  file_path_dict: {!r}\n'.format(indent, self.file_path_dict)
        output += '{}  executable_dict: {!r}\n'.format(indent, self.executable_dict)
        output += '{}  runnable_step_list: {!r}\n'.format(indent, self.runnable_step_list)
        output += '{}  debug: {!r}\n'.format(indent, self.debug)

        output += '{}  Python dict of Python str (file path) objects:\n'.format(indent)
        keys = self.file_path_dict.keys()
        keys.sort(cmp=lambda x, y: cmp(x, y))
        for key in keys:
            assert isinstance(key, str)
            output += '{}    Key: {!r} file_path: {!r}\n'.format(indent, key, self.file_path_dict[key])

        output += '{}  Python dict of Executable objects:\n'.format(indent)
        keys = self.executable_dict.keys()
        keys.sort(cmp=lambda x, y: cmp(x, y))
        for key in keys:
            assert isinstance(key, str)
            output += '{}    Key: {!r} Executable: {!r}\n'.format(indent, key, self.executable_dict[key])
            executable = self.executable_dict[key]
            assert isinstance(executable, Executable)
            output += executable.trace(level=level + 2)

        output += '{}  Python list of RunnableStep objects:\n'.format(indent)
        for runnable_step in self.runnable_step_list:
            assert isinstance(runnable_step, RunnableStep)
            output += runnable_step.trace(level=level + 1)

        return output

    def add_executable(self, executable):
        """Add an C{Executable}.

        @param executable: C{Executable}
        @type executable: bsf.process.Executable
        @return: C{Executable}
        @rtype: bsf.process.Executable
        @raise Exception: An C{Executable.name} already exists in the C{Runnable}
        """

        assert isinstance(executable, Executable)

        if executable.name in self.executable_dict:
            raise Exception("An Executable object with name {!r} already exists in Runnable object {!r}.".
                            format(executable.name, self.name))
        else:
            self.executable_dict[executable.name] = executable

        return executable

    def add_runnable_step(self, runnable_step=None):
        """Convenience method to facilitate initialising, adding and retuning a C{RunnableStep}.

        @param runnable_step: C{RunnableStep}
        @type runnable_step: bsf.process.RunnableStep
        @return: C{RunnableStep}
        @rtype: bsf.process.RunnableStep
        """

        if runnable_step is None:
            return

        assert isinstance(runnable_step, RunnableStep)

        self.runnable_step_list.append(runnable_step)

        return runnable_step

    def run_executable(self, name):
        """Run an C{Executable} defined in the C{Runnable} object.

        @param name: C{Executable.name}
        @type name: str
        @return:
        @rtype:
        @raise Exception: Child process failed with return code or received a signal
        """

        executable = self.executable_dict[name]
        assert isinstance(executable, Executable)
        child_return_code = executable.run()

        if child_return_code > 0:
            raise Exception('[{}] Child process {!r} failed with return code {}'.
                            format(datetime.datetime.now().isoformat(), executable.name, +child_return_code))
        elif child_return_code < 0:
            raise Exception('[{}] Child process {!r} received signal {}.'.
                            format(datetime.datetime.now().isoformat(), executable.name, -child_return_code))
        else:
            return

    @property
    def pickler_path(self):
        """Get the Python C{pickle.Pickler} file path.

        @return: Python C{pickle.Pickler} file path
        @rtype: str | unicode
        """

        return os.path.join(self.working_directory, '.'.join((self.name, 'pkl')))

    def to_pickler_path(self):
        """Write this C{Runnable} object as a Python C{pickle.Pickler} file into the working directory.
        @return:
        @rtype:
        """

        pickler_file = open(self.pickler_path, 'wb')
        pickler = Pickler(file=pickler_file, protocol=HIGHEST_PROTOCOL)
        pickler.dump(obj=self)
        pickler_file.close()

        return

    @classmethod
    def from_pickler_path(cls, file_path):
        """Create a C{Runnable} object from a Python C{pickle.Pickler} file via Python C{pickle.Unpickler}.

        @param file_path: File path to a Python C{pickle.Pickler} file
        @type file_path: str | unicode
        @return: C{Runnable}
        @rtype: Runnable
        """

        pickler_file = open(file_path, 'rb')
        unpickler = Unpickler(file=pickler_file)
        runnable = unpickler.load()
        pickler_file.close()

        assert isinstance(runnable, Runnable)

        return runnable

    @property
    def get_relative_status_path(self):
        """Get the relative status file path indicating successful completion of this C{Runnable}.

        @return: Relative status file path
        @rtype: str
        """

        return '_'.join((self.name, 'completed.txt'))

    @property
    def get_relative_temporary_directory_path(self):
        """Get the relative temporary directory path for this C{Runnable}.

        @return: Relative temporary directory path
        @rtype: str
        """

        return '_'.join((self.name, 'temporary'))

    @property
    def get_absolute_status_path(self):
        """Get the absolute status file path including the C{Runnable.working_directory}.

        @return: Absolute status file path
        @rtype: str
        """

        return os.path.join(self.working_directory, self.get_relative_status_path)

    @property
    def get_absolute_temporary_directory_path(self):
        """Get the absolute temporary directory path including the  C{Runnable.working_directory}.

        @return: Absolute temporary directory path
        @rtype: str
        """

        return os.path.join(self.working_directory, self.get_relative_temporary_directory_path)
