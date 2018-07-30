"""bsf.executables

A package of classes and methods supporting executable programs and scripts.
"""

#
# Copyright 2013 - 2018 Michael K. Schuster
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


import bsf
import bsf.process


class Bowtie2(bsf.process.Executable):
    """Bowtie2 short read aligner class."""

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.Bowtie2} object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(Bowtie2, self).__init__(name=name, program='bsf_chipseq_run_bowtie2.bash')

        section = analysis.configuration.section_from_instance(self)
        self.set_configuration(configuration=analysis.configuration, section=section)

        # Set default Bowtie2 options.

        # None for the moment.


class BWA(bsf.process.Executable):
    """Burrows-Wheeler Aligner (C{bsf.executables.BWA}) class.

    Reference: http://bio-bwa.sourceforge.net/
    Usage: bwa mem db_prefix reads.fq [mates.fq]
    """

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.BWA} object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(BWA, self).__init__(name=name, program='bwa', sub_command=bsf.process.Command(program='mem'))

        # The options have to be set for the 'mem' sub-command.
        section = analysis.configuration.section_from_instance(self)
        self.sub_command.set_configuration(configuration=analysis.configuration, section=section)

        # Set default BWA mem options.

        # None for the moment.


class TopHat(bsf.process.Executable):
    """C{bsf.executables.TopHat} RNA-Seq aligner class.

    Reference: http://tophat.cbcb.umd.edu/manual.html
    Usage: tophat [options]* <index_base> <reads1_1[,...,readsN_1]> [reads1_2,...readsN_2]
    Arguments:
    <ebwt_base> Base name of the index to be searched.
    <reads1_1[,...,readsN_1]>
    <[reads1_2,...readsN_2]>
    """

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.TopHat} object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(TopHat, self).__init__(name=name, program='tophat2')

        section = analysis.configuration.section_from_instance(self)
        self.set_configuration(configuration=analysis.configuration, section=section)

        # Set default TopHat options.

        # None for the moment.


class Macs14(bsf.process.Executable):
    """Model-based Analysis for ChIP-Seq (MACS) version 1.4 peak-caller class (C{bsf.executables.Macs14}).

    Reference: http://liulab.dfci.harvard.edu/MACS/
    """

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.Macs14} (MACS 1.4) object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(Macs14, self).__init__(name=name, program='macs14')

        section = analysis.configuration.section_from_instance(self)
        self.set_configuration(configuration=analysis.configuration, section=section)

        # Set default Macs options.

        if not ('gsize' in self.options and self.options['gsize']):
            raise Exception(
                "A 'gsize' option is required in the {!r} configuration section.".format(section))


class Macs2Bdgcmp(bsf.process.Executable):
    """Model-based Analysis for ChIP-Seq (MACS) version 2 bedGraph comparison class (C{bsf.executables.Macs2Bdgcmp}).

    Reference: http://liulab.dfci.harvard.edu/MACS/
    """

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.Macs2Bdgcmp} (MACS2 BedGraph Comparison) object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(Macs2Bdgcmp, self).__init__(
            name=name,
            program='bsf_chipseq_run_macs2.bash',
            sub_command=bsf.process.Command(program='bdgcmp'))

        # The options have to be set for the 'bdgcmp' sub-command.
        section = analysis.configuration.section_from_instance(self)
        self.sub_command.set_configuration(configuration=analysis.configuration, section=section)

        # Set default Macs options.

        # None for the moment.


class Macs2Callpeak(bsf.process.Executable):
    """Model-based Analysis for ChIP-Seq (MACS) version 2 peak-caller class (C{bsf.executables.Macs2Callpeak}).

    Reference: http://liulab.dfci.harvard.edu/MACS/
    """

    def __init__(self, name, analysis):
        """Initialise a C{bsf.executables.Macs2Callpeak} (MACS 2.0 peak caller) object.

        @param name: Name
        @type name: str
        @param analysis: C{bsf.Analysis}
        @type analysis: bsf.Analysis
        @return:
        @rtype:
        """
        super(Macs2Callpeak, self).__init__(
            name=name,
            program='bsf_chipseq_run_macs2.bash',
            sub_command=bsf.process.Command(program='callpeak'))

        # The options have to be set for the 'callpeak' sub-command.
        section = analysis.configuration.section_from_instance(self)
        self.sub_command.set_configuration(configuration=analysis.configuration, section=section)

        # Set default Macs options.

        if not ('gsize' in self.sub_command.options and self.sub_command.options['gsize']):
            raise Exception(
                "A 'gsize' option is required in the {!r} configuration section.".format(section))
