#! /usr/bin/env python
#
# BSF Python script to summarise an Illumina Run Folder.
#
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

import argparse
import datetime
import os.path
import string

from bsf import Default
from bsf.illumina import RunFolder


parser = argparse.ArgumentParser(description='Summarise an Illumina Run Folder.')

parser.add_argument(
    '--debug',
    help='Debug level',
    required=False,
    type=int)

parser.add_argument(
    '--check',
    action='store_true',
    help='check for completeness',
    required=False)

parser.add_argument(
    'file_path',
    help='File path to an Illumina Run Folder')

name_space = parser.parse_args()

file_path = Default.get_absolute_path(
    file_path=name_space.file_path,
    default_path=Default.absolute_runs_illumina())

irf = RunFolder.from_file_path(file_path=file_path)

print 'Flow Cell Identifier: {}_{}'.format(irf.run_parameters.get_experiment_name,
                                           irf.run_parameters.get_flow_cell_barcode)
print 'Read Structure: {}'.format(string.join(words=irf.run_information.get_read_structure_list, sep=' + '))

file_path_start = os.path.join(file_path, 'First_Base_Report.htm')
if os.path.exists(file_path_start):
    print 'Start date:     {}'.format(datetime.date.fromtimestamp(os.stat(file_path_start).st_mtime))

file_path_end = os.path.join(file_path, 'RTAComplete.txt')
if os.path.exists(file_path_end):
    print 'End date:       {}'.format(datetime.date.fromtimestamp(os.stat(file_path_end).st_mtime))

print 'Experiment:     {}'.format(irf.run_parameters.get_experiment_name)
print 'Flow Cell:      {}'.format(irf.run_parameters.get_flow_cell_barcode)

position = irf.run_parameters.get_position
if position:
    print 'Position:       {}'.format(irf.run_parameters.get_position)

print 'Run Identifier: {}'.format(irf.run_information.run_identifier)
print 'Application Name: {}'.format(irf.run_parameters.get_application_name)
print 'Application Version: {}'.format(irf.run_parameters.get_application_version)
print 'RTA Version:    {}'.format(irf.run_parameters.get_real_time_analysis_version)

if name_space.check:
    irf.check(debug=name_space.debug)
