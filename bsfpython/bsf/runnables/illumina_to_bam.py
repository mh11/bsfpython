"""bsf.runnables.illumina_to_bam

A package of classes and methods to run C{IlluminaToBam} C{Analysis} processes.
"""

#
# Copyright 2013 - 2014 Michael K. Schuster
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

import errno
import os
import shutil

from bsf import Runnable


def run_illumina_to_bam(runnable):
    """Run the I{illumina_to_bam} C{Executable} defined in the C{Runnable}.

    @param runnable: C{Runnable}
    @type runnable: Runnable
    """

    if os.path.exists(path=runnable.file_path_dict['unsorted_md5']) \
            and os.path.getsize(filename=runnable.file_path_dict['unsorted_md5']):
        return

    runnable.run_executable(name='illumina_to_bam')


def run_picard_sort_sam(runnable):
    """Run the I{picard_sort_sam} C{Executable} defined in the C{Runnable}.

    @param runnable: C{Runnable}
    @type runnable: Runnable
    """

    if os.path.exists(path=runnable.file_path_dict['sorted_md5']) \
            and os.path.getsize(filename=runnable.file_path_dict['sorted_md5']):
        return

    run_illumina_to_bam(runnable=runnable)

    runnable.run_executable(name='picard_sort_sam')

    # Remove the now redundant sorted BAM and MD5 checksum files.
    for file_key in ('unsorted_bam', 'unsorted_md5'):
        if os.path.exists(runnable.file_path_dict[file_key]):
            os.remove(runnable.file_path_dict[file_key])


def run(runnable):
    """Run the the C{Runnable}.

    @param runnable: C{Runnable}
    @type runnable: Runnable
    """

    path_temporary = runnable.file_path_dict['temporary_directory']

    if not os.path.isdir(path_temporary):
        try:
            os.makedirs(path_temporary)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    #  Run all Executable objects of this Runnable.

    run_picard_sort_sam(runnable=runnable)

    # Remove the temporary directory and everything within it.

    shutil.rmtree(path=path_temporary, ignore_errors=False)

    # Job done.
