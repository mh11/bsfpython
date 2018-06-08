#! /usr/bin/env python
#
# BSF Python script to test library functions.
#
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


from __future__ import print_function

import datetime
import math
import re
import subprocess
import sys
import threading

import bsf.argument
from bsf.process import Executable


def bsf_test_argument():
    print('Parsed via bsf.argument.Argument.from_key_value()')
    for key, value in (
            ('-switch_short', None),
            ('--switch_long', None),
            ('-option', 'short'),
            ('--option', 'long'),
            ('option', 'pair'),
            ('option', 'pair space'),
            ('-option_pair=short', None),
            ('--option_pair=long', None),
            ('--option=pair space', None)):
        argument = bsf.argument.Argument.from_key_value(key=key, value=value)
        print(argument, argument.get_str(), argument.get_list())

    print()

    print('Instantiated directly via class method')
    argument_list = [
        bsf.argument.Switch(key='key'),
        bsf.argument.SwitchLong(key='key'),
        bsf.argument.SwitchShort(key='key'),
        # Single values
        bsf.argument.Option(key='key', value='value'),
        bsf.argument.OptionLong(key='key', value='value'),
        bsf.argument.OptionShort(key='key', value='value'),
        bsf.argument.OptionPair(key='key', value='value'),
        bsf.argument.OptionPairShort(key='key', value='value'),
        bsf.argument.OptionPairLong(key='key', value='value'),
        bsf.argument.OptionMulti(key='key', value='value'),
        bsf.argument.OptionMultiLong(key='key', value='value'),
        bsf.argument.OptionMultiShort(key='key', value='value'),
        bsf.argument.OptionMultiPair(key='key', value='value'),
        bsf.argument.OptionMultiPairLong(key='key', value='value'),
        bsf.argument.OptionMultiPairShort(key='key', value='value'),
        # Multiple values
        bsf.argument.Option(key='key', value='value1 value2'),
        bsf.argument.OptionLong(key='key', value='value1 value2'),
        bsf.argument.OptionShort(key='key', value='value1 value2'),
        bsf.argument.OptionPair(key='key', value='value1 value2'),
        bsf.argument.OptionPairShort(key='key', value='value1 value2'),
        bsf.argument.OptionPairLong(key='key', value='value1 value2'),
        bsf.argument.OptionMulti(key='key', value='value1 value2'),
        bsf.argument.OptionMultiLong(key='key', value='value1 value2'),
        bsf.argument.OptionMultiShort(key='key', value='value1 value2'),
        bsf.argument.OptionMultiPair(key='key', value='value1 value2'),
        bsf.argument.OptionMultiPairLong(key='key', value='value1 value2'),
        bsf.argument.OptionMultiPairShort(key='key', value='value1 value2'),
    ]

    for argument in argument_list:
        print(argument, argument.get_str(), argument.get_list())

    print()

    return


def bsf_test_thread(file_handle, thread_lock, debug, executable):
    """Thread callable to parse the SLURM process identifier and set it in the C{Executable}.

    @param file_handle: File handle (i.e. pipe)
    @type file_handle: file
    @param thread_lock: Thread lock
    @type thread_lock: threading.lock
    @param debug:
    @param executable: C{Executable}
    @type executable: bsf.process.Executable
    @return:
    """
    for line in file_handle:
        match = re.search(pattern=r'Submitted batch job (\d+)', string=line)
        thread_lock.acquire(True)
        if debug > 0:
            print('Line:', line)
        if match:
            executable.process_identifier = match.group(1)
        else:
            print('Could not parse the process identifier from the SLURM sbatch response line', line)
            executable.process_identifier = '9999999'
            executable.process_name = 'testing successful'
        thread_lock.release()

    return


def bsf_test_subprocess(
        maximum_attempts=3,
        max_thread_joins=10,
        thread_join_timeout=10,
        debug=1):
    """Test the Python subprocess module.

    @param maximum_attempts: Maximum number of attempts to run
    @type maximum_attempts: int
    @param max_thread_joins: Maximum number of attempts to join threads
    @type max_thread_joins: int
    @param thread_join_timeout: Thread join timeout
    @type thread_join_timeout: int
    @param debug: Debug level
    @type debug: int
    @return: Child return code
    @rtype: int
    """
    executable = Executable(name='bsf_test', program='ls')
    executable.add_switch_short(key='a')
    executable.add_switch_short(key='l')
    # Conclusion:
    # The following re-directions only work, if the Popen() call is allowed to use the shell i.e. Popen(shell=True)
    # '1>bsf_test_stdout_redirect.txt'
    # '2>bsf_test_stderr_redirect.txt'
    # However, if the shell is used, the command has to be specified as a single string rather than a list.
    # stdout_path = "bsf_test_stdout.txt"
    stderr_path = "bsf_test_stderr.txt"

    on_posix = 'posix' in sys.builtin_module_names

    child_return_code = 0
    attempt_counter = 0

    while attempt_counter < maximum_attempts:
        child_process = subprocess.Popen(
            args=executable.command_list(),
            bufsize=4096,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=on_posix)

        thread_lock = threading.Lock()

        # thread_out = Thread(
        #     target=Executable.process_stdout,
        #     kwargs={
        #         'stdout_handle': child_process.stdout,
        #         'thread_lock': thread_lock,
        #         'stdout_path': stdout_path,
        #         'debug': debug,
        #     })
        thread_out = threading.Thread(
            target=bsf_test_thread,
            kwargs={
                'file_handle': child_process.stdout,
                'thread_lock': thread_lock,
                'debug': debug,
                'executable': executable,
            })
        thread_out.daemon = True  # Thread dies with the program.
        thread_out.start()

        thread_err = threading.Thread(
            target=Executable.process_stderr,
            kwargs={
                'stderr_handle': child_process.stderr,
                'thread_lock': thread_lock,
                'stderr_path': stderr_path,
                'debug': debug,
            })
        thread_err.daemon = True  # Thread dies with the program.
        thread_err.start()

        # Wait for the child process to finish.

        child_return_code = child_process.wait()

        thread_join_counter = 0

        while thread_out.is_alive() and thread_join_counter < max_thread_joins:
            thread_lock.acquire(True)
            if debug > 0:
                print('[{}] Waiting for STDOUT processor to finish.'.format(
                    datetime.datetime.now().isoformat()))
            thread_lock.release()

            thread_out.join(timeout=thread_join_timeout)
            thread_join_counter += 1

        thread_join_counter = 0

        while thread_err.is_alive() and thread_join_counter < max_thread_joins:
            thread_lock.acquire(True)
            if debug > 0:
                print('[{}] Waiting for STDERR processor to finish.'.format(
                    datetime.datetime.now().isoformat()))
            thread_lock.release()

            thread_err.join(timeout=thread_join_timeout)
            thread_join_counter += 1

        if child_return_code > 0:
            if debug > 0:
                print('[{}] Child process {!r} failed with exit code {}'.format(
                    datetime.datetime.now().isoformat(), executable.name, +child_return_code))
            attempt_counter += 1
        elif child_return_code < 0:
            if debug > 0:
                print('[{}] Child process {!r} received signal {}.'.format(
                    datetime.datetime.now().isoformat(), executable.name, -child_return_code))
        else:
            if debug > 0:
                print('[{}] Child process {!r} completed successfully {}.'.format(
                    datetime.datetime.now().isoformat(), executable.name, +child_return_code))
            break
    else:
        if debug > 0:
            print('[{}] Runnable {!r} exceeded the maximum retry counter {}.'.format(
                datetime.datetime.now().isoformat(), executable.name, maximum_attempts))

    sys.stdout.writelines(executable.trace(level=0))

    return child_return_code


class ExecutableTest(Executable):

    def __init__(
            self,
            name=None,
            program=None,
            options=None,
            arguments=None,
            sub_command=None,
            stdout_path=None,
            stderr_path=None,
            dependencies=None,
            hold=None,
            submit=True,
            maximum_attempts=1,
            process_identifier=None,
            process_name=None,
            stdin_callable=None,
            stdin_kwargs=None,
            stdout_callable=None,
            stdout_kwargs=None,
            stderr_callable=None,
            stderr_kwargs=None):

        super(ExecutableTest, self).__init__(
            name=name,
            program=program,
            options=options,
            arguments=arguments,
            sub_command=sub_command,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            dependencies=dependencies,
            hold=hold,
            submit=submit,
            maximum_attempts=maximum_attempts,
            process_identifier=process_identifier,
            process_name=process_name
        )

        self.stdin_callable = stdin_callable
        self.stdin_kwargs = stdin_kwargs
        self.stdout_callable = stdout_callable
        self.stdout_kwargs = stdout_kwargs
        self.stderr_callable = stderr_callable
        self.stderr_kwargs = stderr_kwargs

        return

    def run(self, max_thread_joins=10, thread_join_timeout=10, debug=0):

        # super(ExecutableTest, self).run(
        #     max_thread_joins=max_thread_joins,
        #     thread_join_timeout=thread_join_timeout,
        #     debug=debug)

        on_posix = 'posix' in sys.builtin_module_names

        child_return_code = 0
        attempt_counter = 0

        while attempt_counter < self.maximum_attempts:

            child_process = subprocess.Popen(
                args=self.command_list(),
                bufsize=0,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=on_posix)
            # TODO: It would be wonderful to catch Exceptions here.
            # OSError: [Errno 2] No such file or directory

            # Two threads, thread_out and thread_err reading STDOUT and STDERR, respectively,
            # should make sure that buffers are not filling up.

            thread_lock = threading.Lock()

            if self.stdin_callable is not None:
                self.stdin_kwargs['thread_lock'] = thread_lock
                thread_in = threading.Thread(
                    target=self.stdin_callable,
                    kwargs=self.stdin_kwargs)
                thread_in.daemon = True  # Thread dies with the program.
                thread_in.start()

            if self.stdout_callable is None:
                thread_out = threading.Thread(
                    target=Executable.process_stdout,
                    kwargs={
                        'stdout_handle': child_process.stdout,
                        'thread_lock': thread_lock,
                        'stdout_path': self.stdout_path,
                        'debug': debug,
                    })
            else:
                self.stdout_kwargs['stdout_handle'] = child_process.stdout
                self.stdout_kwargs['thread_lock'] = thread_lock
                thread_out = threading.Thread(
                    target=self.stdout_callable,
                    kwargs=self.stdout_kwargs)
                thread_out.daemon = True  # Thread dies with the program.
                thread_out.start()

            if self.stderr_callable is None:
                thread_err = threading.Thread(
                    target=Executable.process_stderr,
                    kwargs={
                        'stderr_handle': child_process.stderr,
                        'thread_lock': thread_lock,
                        'stderr_path': self.stderr_path,
                        'debug': debug,
                    })
            else:
                self.stdout_kwargs['stderr_handle'] = child_process.stderr
                self.stdout_kwargs['thread_lock'] = thread_lock
                thread_err = threading.Thread(
                    target=self.stderr_callable,
                    kwargs=self.stderr_kwargs)
            thread_err.daemon = True  # Thread dies with the program.
            thread_err.start()

            # Wait for the child process to finish.

            child_return_code = child_process.wait()

            thread_join_counter = 0

            while thread_out.is_alive() and thread_join_counter < max_thread_joins:
                thread_lock.acquire(True)
                if debug > 0:
                    print('[{}] Waiting for STDOUT processor to finish.'.format(
                        datetime.datetime.now().isoformat()))
                thread_lock.release()

                thread_out.join(timeout=thread_join_timeout)
                thread_join_counter += 1

            thread_join_counter = 0

            while thread_err.is_alive() and thread_join_counter < max_thread_joins:
                thread_lock.acquire(True)
                if debug > 0:
                    print('[{}] Waiting for STDERR processor to finish.'.format(
                        datetime.datetime.now().isoformat()))
                thread_lock.release()

                thread_err.join(timeout=thread_join_timeout)
                thread_join_counter += 1

            if child_return_code > 0:
                if debug > 0:
                    print('[{}] Child process {!r} failed with exit code {}'.format(
                        datetime.datetime.now().isoformat(), self.name, +child_return_code))
                attempt_counter += 1
            elif child_return_code < 0:
                if debug > 0:
                    print('[{}] Child process {!r} received signal {}.'.format(
                        datetime.datetime.now().isoformat(), self.name, -child_return_code))
            else:
                if debug > 0:
                    print('[{}] Child process {!r} completed successfully {}.'.format(
                        datetime.datetime.now().isoformat(), self.name, +child_return_code))
                break

        else:
            if debug > 0:
                print('[{}] Runnable {!r} exceeded the maximum retry counter {}.'.format(
                    datetime.datetime.now().isoformat(), self.name, self.maximum_attempts))

        return child_return_code


class Interval(object):
    def __init__(self, sequence, start, end, strand, name):
        """Initialise an C{Interval} object.

        @param sequence:
        @type sequence: str
        @param start:
        @type start: int
        @param end:
        @type end: int
        @param strand:
        @type strand: int
        @param name:
        @type name: str
        """
        self.sequence = sequence
        self.start = start
        self.end = end
        self.strand = strand
        self.name = name

        return

    def __len__(self):
        return self.end - self.start + 1


def bsf_bundle_intervals(file_path=None, tiles=1):
    total_length = 0
    """ @type total_length: int """

    interval_list = list()
    """ @type interval_list: list[Interval] """

    interval_file = open(file_path, 'r')
    for line in interval_file:
        if line.startswith('@'):
            continue

        line_list = line.split()
        interval = Interval(
            sequence=line_list[0],
            start=int(line_list[1]),
            end=int(line_list[2]),
            strand=int(line_list[3] + '1'),  # Turn +/- into +1/-1.
            name=line_list[4])
        interval_list.append(interval)
        total_length += len(interval)

    interval_file.close()

    print('Interval number:', len(interval_list))
    print('Total length:', total_length)

    cumulative_interval = 0
    """ @type cumulative_interval: int """

    tile_length = total_length / tiles
    print('Tile length:', tile_length)

    tile_list = list()
    """ @type tile_list: list[list[Interval]] """

    for interval in interval_list:
        tile_index = int(math.floor(cumulative_interval / tile_length))
        if len(tile_list) < tile_index + 1:
            tile_list.append(list())

        tile_list[tile_index].append(interval)
        cumulative_interval += len(interval)

    # Print the number of list components for each index.

    for index_list in tile_list:
        cumulative_interval = 0
        """ @type cumulative_interval: int """
        for interval in index_list:
            cumulative_interval += len(interval)
        print('Tile index items: ', len(index_list))
        print('Tile index length:', cumulative_interval)

    return


bsf_bundle_intervals(
    file_path='/data/groups/lab_bsf/resources/interval_lists/TruSight_One_targeted_regions_b37.interval_list',
    tiles=10)
# bsf_test_argument()
