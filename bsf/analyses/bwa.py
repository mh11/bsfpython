# -*- coding: utf-8 -*-
"""BWA Analysis module

A package of classes and methods supporting Burrows-Wheeler Aligner (BWA) analyses.
"""
#  Copyright 2013 - 2019 Michael K. Schuster
#
#  Biomedical Sequencing Facility (BSF), part of the genomics core facility
#  of the Research Center for Molecular Medicine (CeMM) of the
#  Austrian Academy of Sciences and the Medical University of Vienna (MUW).
#
#
#  This file is part of BSF Python.
#
#  BSF Python is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  BSF Python is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with BSF Python.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import print_function

import os

import bsf
import bsf.analyses.aligner
import bsf.connector
import bsf.process


class MaximalExactMatches(bsf.analyses.aligner.Aligner):
    """The C{bsf.analyses.bowtie.MaximalExactMatches} class represents the BWA Maximal Exact Matches (MEM) algorithm.

    Attributes:
    """
    name = 'BWA Maximal Exact Matches Analysis'
    prefix = 'bwa_mem'

    def add_runnable_step_aligner(self, runnable_align, stage_align, file_path_1, file_path_2):
        """Add a BWA MEM-specific C{bsf.process.RunnableStep} to the C{bsf.procedure.ConcurrentRunnable}.

        @param runnable_align: C{bsf.procedure.ConcurrentRunnable}
        @type runnable_align: bsf.procedure.ConcurrentRunnable
        @param stage_align: C{bsf.Stage}
        @type stage_align: bsf.Stage
        @param file_path_1: FASTQ file path 1
        @type file_path_1: str | unicode | None
        @param file_path_2: FASTQ file path 2
        @type file_path_2: str | unicode | None
        @return:
        @rtype:
        """
        file_path_align = bsf.analyses.aligner.FilePathAlign(prefix=runnable_align.name)

        runnable_step = bsf.process.RunnableStep(
                name='bwa_mem',
                program='bwa',
                sub_command=bsf.process.Command(name='mem', program='mem'),
                stdout=bsf.connector.ConnectorFile(file_path=file_path_align.stdout_txt, file_mode='wt'),
                stderr=bsf.connector.ConnectorFile(file_path=file_path_align.stderr_txt, file_mode='wt'))
        runnable_align.add_runnable_step(runnable_step=runnable_step)

        sub_command = runnable_step.sub_command
        # -t [1] Number of threads
        sub_command.add_option_short(key='t', value=str(stage_align.threads))
        # Output errors only.
        sub_command.add_option_short(key='v', value='1')
        # Mark shorter split hits as secondary (for Picard compatibility).
        sub_command.add_switch_short(key='M')
        # Output file [standard output]
        sub_command.add_option_short(key='o', value=file_path_align.aligned_sam)
        # -H header lines
        # -R @RG line
        sub_command.arguments.append(self.genome_index)
        sub_command.arguments.append(file_path_1)
        if file_path_2:
            sub_command.arguments.append(file_path_2)

        return

    def run(self):
        """Run a C{bsf.analyses.bowtie.Bowtie2} analysis.

        @return:
        @rtype:
        """
        # Check for the project name already here,
        # since the super class method has to be called later.
        if not self.project_name:
            raise Exception('A ' + self.name + " requires a 'project_name' configuration option.")

        # Get the sample annotation sheet.

        if self.sas_file:
            self.sas_file = self.configuration.get_absolute_path(file_path=self.sas_file)
            if not os.path.exists(self.sas_file):
                raise Exception('Sample annotation file ' + repr(self.sas_file) + ' does not exist.')
        else:
            self.sas_file = self.get_annotation_file(prefix_list=[MaximalExactMatches.prefix], suffix='samples.csv')
            if not self.sas_file:
                raise Exception('No suitable sample annotation file in the current working directory.')

        # BWA requires the genome.fasta file.
        if not self.genome_index:
            self.genome_index = bsf.standards.FilePath.get_resource_genome_fasta(
                genome_version=self.genome_version,
                genome_index='bwa')

            super(MaximalExactMatches, self).run()

        return