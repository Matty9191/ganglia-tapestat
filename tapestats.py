# Script: tapestats.py
# Author: Matty
# Purpose:
#    This script exposes the tape statistics that are availabe
#    in /sys/class/scsi_tape/{drive}/stats. To read more about
#    these statistics please man tapestat(1).

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
tape_stats = defaultdict(lambda: defaultdict(int))

# Save the previous time so we can average 
# the values over a period of time 
previous_time = 0


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
    previous_value = tape_stats[tape_drive][metric]

    tape_stats[tape_drive][metric] = current_value
    return delta(current_value, previous_value)


def delta(val1, val2):
    """
       Return the difference between val1 and val2
    """
    global previous_time 

    current_time = time.time()
    elapsed_time = current_time - previous_time
    previous_time = current_time
    diff = (val1 - val2) / elapsed_time
    
    if diff == 0:
        debug("No calc required returning a delta of 0")
        return 0
    else:
        debug("Performing calculation %s - %s / %s" % (val1, val2, elapsed_time))
        debug("Returning a delta of %s" % diff)
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

    previous_time = time.time()
    tape_stats[tape_drive][metric] = get_drive_statistic(tape_drive, metric)
    debug("Set tape drive %s metric %s to %s" % (tape_drive,
                                                 metric,
                                                 tape_stats[tape_drive][metric]))


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
    params = [ "tapestats_nst0_write_byte_cnt",
               "tapestats_nst0_write_cnt",
               "tapestats_nst1_write_byte_cnt",
               "tapestats_nst1_write_cnt",
               "tapestats_nst2_write_byte_cnt",
               "tapestats_nst2_write_cnt",
               "tapestats_nst3_write_byte_cnt",
               "tapestats_nst3_write_cnt",
             ]
    metric_init(params)

    for _ in range(10):
        for metric in params:
            stat = update_stats(metric)
            time.sleep(5)
            debug("Value returned for %s is %d" % ("tapestats_nst1_write_byte_cnt", int(stat)))


if __name__ == "__main__":
    main()
