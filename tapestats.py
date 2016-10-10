# Script: tapestats.py
# Author: Matty <matty91@gmail.com>
# Date: 10-05-2016
# Purpose:
#    This script exposes the tape statistics that are availabe
#    in /sys/class/scsi_tape/{drive}/stats. To read more about
#    these statistics please man tapestat(1).
# License: 
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.

import os
import re
import time
from collections import defaultdict

# Enable debugging
DEBUG = 0

# Tape drive metrics to collect
# Described here:
#    https://www.kernel.org/doc/Documentation/scsi/st.txt
TAPE_METRICS = ['read_cnt',
                'write_cnt',
                'read_byte_cnt',
                'write_byte_cnt'
               ]

# Sysfs tape drive location
SYSFS_TAPE_PATH = "/sys/class/scsi_tape/"

# Tape drive statistics
tape_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))


def debug(message):
    """
       Used to print debugging info
    """
    if DEBUG:
        print message


def find_drives():
    """
       Return a list of tape drives
    """
    for drive in os.listdir(SYSFS_TAPE_PATH):
        if re.match(r'^nst[0-9]+$', drive):
            debug("Found drive %s" % drive)
            yield drive


def update_stats(name):
    """
       Ganglia callback used to retrieve stats
    """
    # Parse the name and pull out the tape drive and metric
    first = name.find('_')
    second = name.find('_', first + 1)
    tape_drive = name[first + 1:second]
    metric = name[second + 1:]

    current_value = get_drive_statistic(tape_drive, metric)
    previous_value = tape_stats[tape_drive][metric]["count"]

    current_time = time.time()
    elapsed_time = current_time - tape_stats[tape_drive][metric]["previous_time"]
    tape_stats[tape_drive][metric]["previous_time"] = current_time

    tape_stats[tape_drive][metric]["count"] = current_value
    return delta(current_value, previous_value, elapsed_time)


def delta(val1, val2, elapsed):
    """
       Return the difference between val1 and val2
    """
    diff = (val1 - val2) / elapsed
    
    if diff == 0:
        debug("No calc required returning a delta of 0")
        return 0
    else:
        debug("Performing calculation %f - %f / %f = %f" % (val1, val2, elapsed, diff))
        return diff


def get_drive_statistic(drive_name, metric):
    """
       Get the sysfs statistics for the tape drive passed as an argument
    """
    debug("Opening sysfs file " + SYSFS_TAPE_PATH + drive_name + "/stats/" + metric)
    with open(SYSFS_TAPE_PATH + drive_name + "/stats/" + metric, "r") as f:
        metric_value = f.read()
        debug("Got metric value %d for metric %s" % (int(metric_value), metric))
    return int(metric_value)


def init_tape_drive_metrics(tape_drive, metric):
    """
       Initialize the metrics when we start
    """
    tape_stats[tape_drive][metric]["count"] = get_drive_statistic(tape_drive, metric)
    tape_stats[tape_drive][metric]["previous_time"] = time.time()


def metric_init(params):
    """
        Initialize all of the tape statistics
    """
    descriptors = list()

    for sysfs_value in TAPE_METRICS:
        for tape_drive in find_drives():
            debug("Process metric %s for tape drive %s" % (sysfs_value, tape_drive))
            debug("Metric name -> %s"  % ("tapestat_" + tape_drive + "_" + sysfs_value))
            desc = {
                'name': 'tapestat_' + tape_drive + "_" + sysfs_value,
                'call_back': update_stats,
                'time_max': 60,
                'value_type': 'float',
                'units': sysfs_value + '/s',
                'slope': 'both',
                'format': '%f',
                'description': sysfs_value,
                'groups': 'tapestats'
            }
            init_tape_drive_metrics(tape_drive, sysfs_value)
            descriptors.append(desc)

    return descriptors


def main():
    """
       Main function used for testing
    """
    params = [ 
               #"tapestats_nst0_write_cnt",
               #"tapestats_nst0_write_byte_cnt",
               #"tapestats_nst1_write_cnt",
               #"tapestats_nst1_write_byte_cnt",
               "tapestats_nst2_write_cnt",
               "tapestats_nst2_write_byte_cnt",
               #"tapestats_nst3_write_cnt",
               #"tapestats_nst3_write_byte_cnt"
             ]
    metric_init(params)

    for _ in range(100000):
        for metric in params:
            stat = update_stats(metric)
            time.sleep(1)
            debug("Value returned for %s is %d" % (metric, int(stat)))


if __name__ == "__main__":
    main()
