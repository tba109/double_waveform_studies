import os
import csv
import datetime
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import curve_fit
from scipy.stats import norm
from scipy import signal

# FILE READING/WRITING


# Reads csv file with header and time & voltage columns
# Returns time array, voltage array, and header as a string
def rw(file_name, nhdr):
    header = []
    header_str = ''
    x = np.array([])
    y = np.array([])

    if os.path.isfile(file_name):
        myfile = open(file_name, 'rb')          # Opens waveform file
        for i in range(nhdr):                   # Reads header and saves in a list
            header.append(myfile.readline())
        for line in myfile:
            x = np.append(x, float(line.split(str.encode(','))[0]))     # Reads time values & saves in an array
            y = np.append(y, float(line.split(str.encode(','))[1]))     # Reads voltage values & saves in an array
        myfile.close()                          # Closes waveform file
        head_len = len(header)
        for i in range(0, head_len):            # Converts header list to a string
            head_byte = header[i]
            head_str = head_byte.decode('cp437')
            header_str += head_str

    return x, y, header_str


# Given a time array, voltage array, and header, writes a csv file with header and time & voltage columns
def ww(x, y, file_name, hdr):
    myfile = open(file_name, 'w')           # Opens file to write waveform into
    for entry in str(hdr):                  # Writes header to file
        myfile.write(entry)
    for ix, iy in zip(x, y):                # Writes time and voltage values into file
        line = '%.7E,%f\n' % (ix, iy)
        myfile.write(line)
    myfile.close()                          # Closes waveform file


# Creates text file with time of beginning of spe, time of end of spe, charge, amplitude, fwhm, 10-90 & 20-80 rise
# times, 10-90 & 20-80 fall times, and 10%, 20%, 80% & 90% jitter for an spe file
def save_calculations(dest_path, i, t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10,
                      time20, time80, time90):
    file_name = str(dest_path / 'calculations' / 'D1--waveforms--%05d.txt') % i
    myfile = open(file_name, 'w')
    myfile.write('t1,' + str(t1))
    myfile.write('\nt2,' + str(t2))
    myfile.write('\ncharge,' + str(charge))
    myfile.write('\namplitude,' + str(amplitude))
    myfile.write('\nfwhm,' + str(fwhm))
    myfile.write('\nrise1090,' + str(rise1090))
    myfile.write('\nrise2080,' + str(rise2080))
    myfile.write('\nfall1090,' + str(fall1090))
    myfile.write('\nfall2080,' + str(fall2080))
    myfile.write('\ntime10,' + str(time10))
    myfile.write('\ntime20,' + str(time20))
    myfile.write('\ntime80,' + str(time80))
    myfile.write('\ntime90,' + str(time90))
    myfile.close()


# Creates text file with data from an array
def write_hist_data(array, dest_path, name):
    array = np.sort(array)
    file_name = Path(dest_path / 'hist_data' / name)

    myfile = open(file_name, 'w')
    for item in array:  # Writes an array item on each line of file
        myfile.write(str(item) + '\n')
    myfile.close()


# Checks if a file exists
def check_if_file(path, file_name):
    if os.path.isfile(path / file_name):
        return 'yes'
    else:
        return 'no'


# Reads calculations from existing file
def read_calc(filename):
    myfile = open(filename, 'r')  # Opens file with calculations
    csv_reader = csv.reader(myfile)
    file_array = np.array([])
    for row in csv_reader:  # Creates array with calculation data
        file_array = np.append(file_array, float(row[1]))
    myfile.close()
    t1 = file_array[0]
    t2 = file_array[1]
    charge = file_array[2]
    amp = file_array[3]
    fwhm = file_array[4]
    rise1090 = file_array[5]
    rise2080 = file_array[6]
    fall1090 = file_array[7]
    fall2080 = file_array[8]
    j10 = file_array[9]
    j20 = file_array[10]
    j80 = file_array[11]
    j90 = file_array[12]

    return t1, t2, charge, amp, fwhm, rise1090, rise2080, fall1090, fall2080, j10, j20, j80, j90


# Creates info file
def info_file(acq_date_time, source_path, dest_path, pmt_hv, gain, offset, trig_delay, amp, fsps, band, nfilter, r):
    now = datetime.datetime.now()
    file_name = 'info.txt'
    file = dest_path / file_name
    myfile = open(file, 'w')
    myfile.write('Data acquisition,' + str(acq_date_time))              # date & time of raw data from d0 info file
    myfile.write('\nData processing,' + str(now))                       # current date & time
    myfile.write('\nSource data,' + str(source_path))                   # path to source data
    myfile.write('\nDestination data,' + str(dest_path))                # path to folder of current data
    myfile.write('\nPMT HV (V),' + str(pmt_hv))                         # voltage of PMT from d0 info file
    myfile.write('\nNominal gain,' + str(gain))                         # gain of PMT from d0 info file
    myfile.write('\nDG 535 offset,' + str(offset))                      # offset of pulse generator from d0 info file
    myfile.write('\nDG 535 trigger delay (ns),' + str(trig_delay))      # trigger delay of pulse generator from d0 info
                                                                        # file
    myfile.write('\nDG 535 amplitude (V),' + str(amp))                  # amplitude of pulse generator from d0 info file
    myfile.write('\nOscilloscope sample rate (Hz),' + str(fsps))        # sample rate of oscilloscope from d0 info file
    myfile.write('\nOscilloscope bandwidth (Hz),' + str(band))          # bandwidth of oscilloscope from d0 info file
    myfile.write('\nOscilloscope noise filter (bits),' + str(nfilter))  # oscilloscope noise filter from d0 info file
    myfile.write('\nOscilloscope resistance (ohms),' + str(r))          # resistance of oscilloscope from d0 info file
    myfile.close()


# SORT WAVEFORMS


# Separates files into spe, non-spe, and maybe spe
def p1_sort(file_num, nhdr, fsps, fc, numtaps, data_path, save_path, baseline):
    wc = 2. * np.pi * fc / fsps     # Discrete radial frequency
    lowpass = signal.firwin(numtaps, cutoff=wc/np.pi, window='blackman')    # Blackman windowed lowpass filter

    file_name = str(data_path / 'C2--waveforms--%05d.txt') % file_num
    spe_name = str(save_path / 'd1/d1_raw/D1--waveforms--%05d.txt') % file_num
    spe_not_there = str(save_path / 'd1/not_spe/D1--not_spe--%05d.txt') % file_num
    spe_unsure = str(save_path / 'd1/unsure_if_spe/D1--unsure--%05d.txt') % file_num

    if os.path.isfile(spe_name):    # If file has already been sorted, does not sort it again
        pass
    elif os.path.isfile(spe_not_there):     # If file has already been sorted, does not sort it again
        pass
    elif os.path.isfile(spe_unsure):        # If file has already been sorted, does not sort it again
        pass
    else:                           # If file has not been sorted, sorts it
        t, v, hdr = rw(file_name, nhdr)     # Reads waveform file

        v1 = signal.filtfilt(lowpass, 1.0, v - baseline)        # Applies lowpass filter to voltage array
        v2 = v1[numtaps:len(v1)-1]          # Splices voltage array
        t2 = t[numtaps:len(v1)-1]           # Splices time array

        v_flip = -1 * v2            # Flips voltage array so spe is positive
        peaks, _ = signal.find_peaks(v_flip, 0.001)     # Finds indices of peaks above 0.001 V
        v_peaks = v2[peaks]         # Creates list of voltages where peaks above 0.001 V occur
        t_peaks = t2[peaks]         # Creates list of times where peaks above 0.001 V occur
        check_peaks, _ = signal.find_peaks(v_flip, [0.001, 0.0025])     # Finds peaks between 0.001 V & 0.0025 V
        v_check = v2[check_peaks]   # Creates list of times where peaks between 0.001 V & 0.0025 V occur

        # If no peaks larger than 0.001 V, no spe
        if len(peaks) == 0:
            ww(t2, v2, spe_not_there, hdr)      # Writes filtered waveform to file
            print("Length of /d1_raw/:", len(os.listdir(str(save_path / 'd1/d1_raw/'))))

        # If one peak larger than 0.001 V and it is larger than 0.002 V, spe
        elif len(peaks) == 1 and min(v2[370:1370]) < -0.002:
            ww(t2, v2, spe_name, hdr)           # Writes filtered waveform to file
            print("Length of /d1_raw/:", len(os.listdir(str(save_path / 'd1/d1_raw/'))))

        # If 2 or more peaks larger than 0.001 V, peak is larger than 0.005 V, and all other peaks are smaller than
        # 0.0025, spe
        elif len(peaks) >= 2 and min(v2[370:1370]) < -0.005 and len(peaks) - 1 == len(v_check):
            ww(t2, v2, spe_name, hdr)           # Writes filtered waveform to file
            print("Length of /d1_raw/:", len(os.listdir(str(save_path / 'd1/d1_raw/'))))

        # Otherwise, plots waveform for user to sort manually
        else:
            plt.figure()
            plt.plot(t, v, 'b')         # Plots unfiltered waveform
            plt.plot(t2, v2 + baseline, 'r', linewidth=2.5)         # Plots filtered waveform
            plt.plot(t_peaks, v_peaks + baseline, 'x', color='cyan')        # Plots peaks
            plt.title('File #%05d' % file_num)
            plt.xlabel('Time (s)')
            plt.ylabel('Voltage (V)')
            plt.grid(True)
            print('Displaying file #%05d' % file_num)
            plt.show(block=False)

            spe_check = 'pre-loop initialization'
            while spe_check != 'y' and spe_check != 'n' and spe_check != 'u':
                spe_check = input('Is there a single visible SPE? "y", "n", or "u"\n')
            if spe_check == 'y':
                ww(t2, v2, spe_name, hdr)           # Writes filtered waveform to file
            elif spe_check == 'n':
                ww(t2, v2, spe_not_there, hdr)      # Writes filtered waveform to file
            elif spe_check == 'u':
                ww(t2, v2, spe_unsure, hdr)         # Writes filtered waveform to file
            print('file #%05d: Done' % file_num)
            print("Length of /d1_raw/:", len(os.listdir(str(save_path / 'd1/d1_raw/'))))
            plt.close()

    return


# CALCULATIONS


# Returns the average baseline (baseline noise level)
def calculate_average(t, v):
    v_sum = 0

    idx = np.where(v == min(v))     # Finds index of point of minimum voltage value

    if idx > len(t) / 2:            # If minimum voltage is in second half of voltage array, calculates baseline using
        idx1 = int(.1 * len(t))     # first half of voltage array
        idx2 = int(.35 * len(t))
    else:
        idx1 = int(.65 * len(t))    # If minimum voltage is in first half of voltage array, calculates baseline using
        idx2 = int(.9 * len(t))     # second half of voltage array
    for i in range(idx1, idx2):
        v_sum += v[i]
    average = v_sum / (idx2 - idx1)

    return average


# Shifts spes so that baseline = 0 and when t = 0, v = 50% max
def shift_waveform(file_num, nhdr, data_path, save_path):
    file_name = 'D1--waveforms--%05d.txt' % file_num

    if os.path.isfile(data_path / file_name):
        if os.path.isfile(save_path / file_name):       # If file has already been shifted, does nothing
            pass
        else:
            t, v, hdr = rw(data_path / file_name, nhdr)     # Reads waveform file
            half_max = min(v) / 2                           # Calculates 50% max
            differential = np.diff(v)                       # Calculates derivative of every point in voltage array
            difference_value = np.abs(v - half_max)   # Finds difference between every point in voltage array & 50% max
            for i in range(0, len(differential)):       # Sets every value in difference_value array with a positive
                if differential[i] > 0:                 # derivative equal to infinity
                    difference_value[i] = np.inf
            index = np.argmin(difference_value)  # Finds index of closest voltage to 50% max with a negative derivative
            half_max_time = t[index]            # Finds time at 50% max
            t2 = t - half_max_time              # Subtracts time of 50% max from time array
            avg = calculate_average(t, v)       # Calculates average baseline
            v2 = v - avg                        # Subtracts average baseline voltage from voltage array
            ww(t2, v2, save_path / file_name, hdr)      # Writes shifted waveform to file
            print('Length of /d1_shifted/:', len(os.listdir(str(save_path))))


# Returns charge of spe (as a positive value)
def calculate_charge(t, v, r):
    vsum = 0
    tvals = np.linspace(t[0], t[len(t) - 1], 5000)      # Creates array of times over entire timespan
    vvals = np.interp(tvals, t, v)                      # Interpolates & creates array of voltages over entire timespan

    for i in range(len(tvals)):                         # Calculates sum of all voltages in full timespan
        vsum += vvals[i]
    charge = -1 * (tvals[len(tvals) - 1]) * vsum / (len(tvals) * r)     # Calculates charge

    return charge


# Returns time when spe waveform begins and time when spe waveform ends
def calculate_t1_t2(t, v):
    idx1 = np.inf
    idx2 = np.inf

    min_time = t[np.where(v == min(v))][0]              # Finds time of point of minimum voltage

    tvals = np.linspace(t[0], t[len(t) - 1], 5000)      # Creates array of times over entire timespan
    tvals1 = np.linspace(t[0], min_time, 5000)          # Creates array of times from beginning to point of min voltage
    tvals2 = np.linspace(min_time, t[len(t) - 1], 5000)     # Creates array of times from point of min voltage to end
    vvals1 = np.interp(tvals1, t, v)   # Interpolates & creates array of voltages from beginning to point of min voltage
    vvals2 = np.interp(tvals2, t, v)    # Interpolates & creates array of voltages from point of min voltage to end
    vvals1_flip = np.flip(vvals1)   # Flips array, creating array of voltages from point of min voltage to beginning
    difference_value1 = vvals1_flip - (0.1 * min(v))    # Finds difference between points in beginning array and 10% max
    difference_value2 = vvals2 - (0.1 * min(v))         # Finds difference between points in end array and 10% max

    for i in range(0, len(difference_value1) - 1):  # Starting at point of minimum voltage and going towards beginning
        if difference_value1[i] >= 0:               # of waveform, finds where voltage becomes greater than 10% max
            idx1 = len(difference_value1) - i
            break
    if idx1 == np.inf:      # If voltage never becomes greater than 10% max, finds where voltage is closest to 10% max
        idx1 = len(difference_value1) - 1 - np.argmin(np.abs(difference_value1))
    for i in range(0, len(difference_value2) - 1):      # Starting at point of minimum voltage and going towards end of
        if difference_value2[i] >= 0:                   # waveform, finds where voltage becomes greater than 10% max
            idx2 = i
            break
    if idx2 == np.inf:      # If voltage never becomes greater than 10% max, finds where voltage is closest to 10% max
        idx2 = np.argmin(np.abs(difference_value2))

    t1 = tvals[np.argmin(np.abs(tvals - tvals1[idx1]))]             # Finds time of beginning of spe
    t2 = tvals[np.argmin(np.abs(tvals - tvals2[idx2]))]             # Finds time of end of spe

    return t1, t2


# Returns the amplitude of spe as a positive value (minimum voltage)
def calculate_amp(t, v):
    avg = calculate_average(t, v)       # Calculates value of baseline voltage
    amp = avg - np.amin(v)              # Calculates max amplitude

    return amp


# Returns the full width half max (FWHM) of spe
def calculate_fwhm(t, v):
    half_max = (min(v) / 2).item()                      # Calculates 50% max value
    tvals = np.linspace(t[0], t[len(t) - 1], 5000)      # Creates array of times over entire timespan
    vvals = np.interp(tvals, t, v)                      # Interpolates & creates array of voltages over entire timespan
    difference_value = np.abs(vvals - half_max)         # Finds difference between points in voltage array and 50% max
    index_min = np.argmin(np.abs(vvals - min(v)))       # Finds index of minimum voltage in voltage array
    for i in range(index_min.item(), len(np.diff(vvals)) - 1):  # Sets every value in difference_value array with a
        if np.diff(vvals)[i] < 0:                               # negative differential equal to infinity
            difference_value[i] = np.inf
    difference_value = difference_value[index_min.item():len(vvals) - 1]
    half_max_time = tvals[np.argmin(difference_value) + index_min.item()]   # Finds time of 50% max

    return half_max_time


# Returns rise times of given percentages of amplitude
def rise_time(t, v, low, high):
    percent_low = low / 100
    percent_high = high / 100

    avg = calculate_average(t, v)               # Calculates average baseline
    t1, t2 = calculate_t1_t2(t, v)              # Calculates start time of spe
    min_time = t[np.where(v == min(v))][0]      # Finds time at point of minimum voltage

    val_1 = percent_low * (min(v) - avg)        # Calculates first percent of max
    val_2 = percent_high * (min(v) - avg)       # Calculates second percent of max

    tvals = np.linspace(t1, min_time, 5000) # Creates array of times from beginning of spe to point of minimum voltage
    vvals = np.interp(tvals, t, v)  # Interpolates & creates array of voltages from beginning of spe to minimum voltage

    time_low = tvals[np.argmin(np.abs(vvals - val_1))]          # Finds time of point of first percent of max
    time_high = tvals[np.argmin(np.abs(vvals - val_2))]         # Finds time of point of second percent of max

    risetime = time_high - time_low                             # Calculates rise time
    risetime = float(format(risetime, '.2e'))

    return risetime


# Returns fall times of given percentages of amplitude
def fall_time(t, v, low, high):
    percent_low = low / 100
    percent_high = high / 100

    avg = calculate_average(t, v)               # Calculates average baseline
    t1, t2 = calculate_t1_t2(t, v)              # Calculates start time of spe
    min_time = t[np.where(v == min(v))][0]      # Finds time at point of minimum voltage

    val_1 = percent_high * (min(v) - avg)       # Calculates first percent of max
    val_2 = percent_low * (min(v) - avg)        # Calculates second percent of max

    tvals = np.linspace(min_time, t2, 5000)  # Creates array of times from beginning of spe to point of minimum voltage
    vvals = np.interp(tvals, t, v)  # Interpolates & creates array of voltages from beginning of spe to minimum voltage

    time_high = tvals[np.argmin(np.abs(vvals - val_1))]     # Finds time of point of first percent of max
    time_low = tvals[np.argmin(np.abs(vvals - val_2))]      # Finds time of point of second percent of max

    falltime = time_low - time_high                         # Calculates fall time
    falltime = float(format(falltime, '.2e'))

    return falltime


# Returns percent jitter of a given percent
def calculate_jitter(t, v, per):
    percent = per / 100

    avg = calculate_average(t, v)               # Calculates average baseline
    t1, t2 = calculate_t1_t2(t, v)              # Calculates start time of spe
    min_time = t[np.where(v == min(v))][0]      # Finds time at point of minimum voltage

    val = percent * (min(v) - avg)              # Calculates percent of max
    tvals = np.linspace(t1, min_time, 5000) # Creates array of times from beginning of spe to point of minimum voltage
    vvals = np.interp(tvals, t, v)  # Interpolates & creates array of voltages from beginning of spe to minimum voltage

    time = tvals[np.argmin(np.abs(vvals - val))]        # Finds time

    return time


# DOING CALCULATIONS


# Checks if calculated values are possible or not
def check_if_impossible(t1, t2, charge, amp, fwhm, rise1090, rise2080, fall1090, fall2080, j10, j20, j80, j90):
    if (t1 < 0 or t2 <= t1 or charge <= 0 or amp <= 0 or fwhm <= 0 or rise1090 <= 0 or rise2080 <= 0 or fall1090 <= 0 or
            fall2080 <= 0 or j10 >= 0 or j20 >= 0 or j80 <= 0 or j90 <= 0):
        return 'impossible'
    else:
        return 'ok'


# Creates empty arrays for calculations
def initialize_arrays():

    t1_array = np.array([])
    t2_array = np.array([])
    charge_array = np.array([])
    amplitude_array = np.array([])
    fwhm_array = np.array([])
    rise1090_array = np.array([])
    rise2080_array = np.array([])
    fall1090_array = np.array([])
    fall2080_array = np.array([])
    time10_array = np.array([])
    time20_array = np.array([])
    time80_array = np.array([])
    time90_array = np.array([])

    return t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, \
        fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array


# Creates array for a calculation
def append_arrays(t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80,
                  time90, t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array,
                  fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array):

    t1_array = np.append(t1_array, t1)
    t2_array = np.append(t2_array, t2)
    charge_array = np.append(charge_array, charge)
    amplitude_array = np.append(amplitude_array, amplitude)
    fwhm_array = np.append(fwhm_array, fwhm)
    rise1090_array = np.append(rise1090_array, rise1090)
    rise2080_array = np.append(rise2080_array, rise2080)
    fall1090_array = np.append(fall1090_array, fall1090)
    fall2080_array = np.append(fall2080_array, fall2080)
    time10_array = np.append(time10_array, time10)
    time20_array = np.append(time20_array, time20)
    time80_array = np.append(time80_array, time80)
    time90_array = np.append(time90_array, time90)

    return t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, \
        fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array


# Removes spe waveform from all spe folders
def remove_spe(path_1, path_2, path_3, number, nhdr):
    t, v, hdr = rw(str(path_1 / 'C2--waveforms--%05d.txt') % number, nhdr)
    ww(t, v, str(path_2 / 'not_spe' / 'D1--not_spe--%05d.txt') % number, hdr)
    if os.path.isfile(str(path_3 / 'D1--waveforms--%05d.txt') % number):
        os.remove(str(path_3 / 'D1--waveforms--%05d.txt') % number)
    if os.path.isfile(str(path_2 / 'd1_raw' / 'D1--waveforms--%05d.txt') % number):
        os.remove(str(path_2 / 'd1_raw' / 'D1--waveforms--%05d.txt') % number)
    if os.path.isfile(str(path_2 / 'calculations' / 'D1--waveforms--%05d.txt') % number):
        os.remove(str(path_2 / 'calculations' / 'D1--waveforms--%05d.txt') % number)


# Calculates beginning & end times of spe waveform, charge, amplitude, fwhm, 10-90 & 20-80 rise times, 10-90 & 20-80
# fall times, and 10%, 20%, 80% & 90% jitter
def calculations(t, v, r):
    charge = calculate_charge(t, v, r)
    t1, t2 = calculate_t1_t2(t, v)
    amp = calculate_amp(t, v)
    fwhm = calculate_fwhm(t, v)
    rt1090 = rise_time(t, v, 10, 90)
    ft1090 = fall_time(t, v, 10, 90)
    rt2080 = rise_time(t, v, 20, 80)
    ft2080 = fall_time(t, v, 20, 80)
    j10 = calculate_jitter(t, v, 10)
    j20 = calculate_jitter(t, v, 20)
    j80 = calculate_jitter(t, v, 80)
    j90 = calculate_jitter(t, v, 90)

    return t1, t2, charge, amp, fwhm, rt1090, rt2080, ft1090, ft2080, j10, j20, j80, j90


# Reads calculations from an existing file and checks if they are possible values
def read_calculations(filename):
    t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80, time90 = \
        read_calc(filename)
    possibility = check_if_impossible(t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090,
                                      fall2080, time10, time20, time80, time90)

    return t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80, time90, \
        possibility


# Removes spe file if values are impossible, appends values to arrays if not, and creates calculations file if it does
# not already exist
def create_arrays(calc_file, path_1, path_2, path_3, number, t1_array, t2_array, charge_array, amplitude_array,
                  fwhm_array, rise1090_array, rise2080_array, fall1090_array, fall2080_array, time10_array,
                  time20_array, time80_array, time90_array, t1, t2, charge, amplitude, fwhm, rise1090, rise2080,
                  fall1090, fall2080, time10, time20, time80, time90, possibility, nhdr):

    # Any spe waveform that returns impossible values is put into the not_spe folder
    if possibility == 'impossible':
        print('Removing file #%05d' % number)
        remove_spe(path_1, path_2, path_3, number, nhdr)

    # All other spe waveforms' calculations are placed into arrays
    else:
        t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, fall1090_array, \
            fall2080_array, time10_array, time20_array, time80_array, time90_array = \
            append_arrays(t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20,
                          time80, time90, t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array,
                          rise2080_array, fall1090_array, fall2080_array, time10_array, time20_array, time80_array,
                          time90_array)
        if not os.path.isfile(calc_file):
            save_calculations(path_2, number, t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080,
                              time10, time20, time80, time90)

    return t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, \
        fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array


# Calculates beginning & end times of spe waveform, charge, amplitude, fwhm, 10-90 & 20-80 rise times, 10-90 & 20-80
# fall times, and 10%, 20%, 80% & 90% jitter for each spe file
# Returns arrays of beginning & end times of spe waveform, charge, amplitude, fwhm, 10-90 & 20-80 rise times, 10-90 &
# 20-80 fall times, and 10%, 20%, 80% & 90% jitter
def make_arrays(save_shift, dest_path, data_sort, start, end, nhdr, r):
    t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, fall1090_array, \
        fall2080_array, time10_array, time20_array, time80_array, time90_array = initialize_arrays()

    for i in range(start, end + 1):
        file_name1 = str(save_shift / 'D1--waveforms--%05d.txt') % i
        file_name2 = str(dest_path / 'calculations' / 'D1--waveforms--%05d.txt') % i

        if os.path.isfile(file_name1):
            # If the calculations were done previously, they are read from a file
            if os.path.isfile(file_name2):
                print("Reading calculations from file #%05d" % i)
                t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80, \
                    time90, possibility = read_calculations(file_name2)
            # If the calculations were not done yet, they are calculated
            else:
                print("Calculating shifted file #%05d" % i)
                t, v, hdr = rw(file_name1, nhdr)        # Shifted waveform file is read
                t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80, time90\
                    = calculations(t, v, r)             # Calculations are done
                possibility = check_if_impossible(t1, t2, charge, amplitude, fwhm, rise1090, rise2080, fall1090,
                                                  fall2080, time10, time20, time80, time90)

            t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, \
                fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array = \
                create_arrays(file_name2, data_sort, dest_path, save_shift, i, t1_array, t2_array, charge_array,
                              amplitude_array, fwhm_array, rise1090_array, rise2080_array, fall1090_array,
                              fall2080_array, time10_array, time20_array, time80_array, time90_array, t1, t2, charge,
                              amplitude, fwhm, rise1090, rise2080, fall1090, fall2080, time10, time20, time80, time90,
                              possibility, nhdr)

    return t1_array, t2_array, charge_array, amplitude_array, fwhm_array, rise1090_array, rise2080_array, \
        fall1090_array, fall2080_array, time10_array, time20_array, time80_array, time90_array


# HISTOGRAMS


# Defines Gaussian function (a is amplitude, b is mean, c is standard deviation)
def func(x, a, b, c):
    gauss = a * np.exp(-(x - b) ** 2.0 / (2 * c ** 2))
    return gauss


# Finds Gaussian fit of array
def gauss_fit(array, bins, n):
    b_est, c_est = norm.fit(array)      # Calculates mean & standard deviation based on entire array
    range_min1 = b_est - c_est          # Calculates lower limit of Gaussian fit (1sigma estimation)
    range_max1 = b_est + c_est          # Calculates upper limit of Gaussian fit (1sigma estimation)
    bins_range1 = np.linspace(range_min1, range_max1, 10000)    # Creates array of bins between upper & lower limits
    n_range1 = np.interp(bins_range1, bins, n)                  # Interpolates & creates array of y axis values
    guess1 = [1, float(b_est), float(c_est)]                    # Defines guess for values of a, b & c in Gaussian fit
    popt1, pcov1 = curve_fit(func, bins_range1, n_range1, p0=guess1, maxfev=10000)      # Finds Gaussian fit
    mu1 = float(format(popt1[1], '.2e'))                        # Calculates mean based on 1sigma guess
    sigma1 = np.abs(float(format(popt1[2], '.2e')))     # Calculates standard deviation based on 1sigma estimation
    range_min2 = mu1 - 2 * sigma1                       # Calculates lower limit of Gaussian fit (2sigma)
    range_max2 = mu1 + 2 * sigma1                       # Calculates upper limit of Gaussian fit (2sigma)
    bins_range2 = np.linspace(range_min2, range_max2, 10000)    # Creates array of bins between upper & lower limits
    n_range2 = np.interp(bins_range2, bins, n)          # Interpolates & creates array of y axis values
    guess2 = [1, mu1, sigma1]                           # Defines guess for values of a, b & c in Gaussian fit
    popt2, pcov2 = curve_fit(func, bins_range2, n_range2, p0=guess2, maxfev=10000)      # Finds Gaussian fit

    return bins_range2, popt2, pcov2


# Creates histogram given an array
def plot_histogram(array, dest_path, nbins, xaxis, title, units, filename):

    path = Path(dest_path / 'plots')
    n, bins, patches = plt.hist(array, nbins)           # Plots histogram
    bins = np.delete(bins, len(bins) - 1)
    bins_diff = bins[1] - bins[0]
    bins = np.linspace(bins[0] + bins_diff / 2, bins[len(bins) - 1] + bins_diff / 2, len(bins))

    bins_range, popt, pcov = gauss_fit(array, bins, n)                  # Finds Gaussian fit
    plt.plot(bins_range, func(bins_range, *popt), color='red')          # Plots Gaussian fit (mean +/- 2sigma)

    mu2 = float(format(popt[1], '.2e'))                 # Calculates mean
    sigma2 = np.abs(float(format(popt[2], '.2e')))      # Calculates standard deviation

    plt.xlabel(xaxis + ' (' + units + ')')
    plt.title(title + ' of SPE\n mean: ' + str(mu2) + ' ' + units + ', SD: ' + str(sigma2) + ' ' + units)
    plt.savefig(path / str(filename + '.png'), dpi=360)         # Plots histogram with Gaussian fit

    write_hist_data(array, dest_path, filename + '.txt')


# AVERAGE WAVEFORM


# Calculates average waveform of spe
def average_waveform(start, end, dest_path, nhdr):
    data_file = Path(dest_path / 'd1_shifted')
    save_file = Path(dest_path / 'plots')
    tsum = 0
    vsum = 0
    n = 0
    for i in range(start, end + 1):
        file_name = 'D1--waveforms--%05d.txt' % i
        if os.path.isfile(data_file / file_name):
            print('Reading file #', i)
            t, v, hdr = rw(data_file / file_name, nhdr)     # Reads a waveform file
            v = v / min(v)                                  # Normalizes voltages
            idx = np.where(t == 0)                          # Finds index of t = 0 point
            idx = int(idx[0])
            t = np.roll(t, -idx)                            # Rolls time array so that t = 0 point is at index 0
            v = np.roll(v, -idx)                            # Rolls voltage array so that 50% max point is at index 0
            idx2 = np.where(t == min(t))                    # Finds index of point of minimum t
            idx2 = int(idx2[0])
            idx3 = np.where(t == max(t))                    # Finds index of point of maximum t
            idx3 = int(idx3[0])
            # Only averages waveform files that have enough points before t = 0 & after the spe
            if idx2 <= 3430:
                # Removes points between point of maximum t & chosen minimum t in time & voltage arrays
                t = np.concatenate((t[:idx3], t[3430:]))
                v = np.concatenate((v[:idx3], v[3430:]))
                # Rolls time & voltage arrays so that point of chosen minimum t is at index 0
                t = np.roll(t, -idx3)
                v = np.roll(v, -idx3)
                if len(t) >= 3920:
                    # Removes points after chosen point of maximum t in time & voltage arrays
                    t = t[:3920]
                    v = v[:3920]
                    # Sums time & voltage arrays
                    tsum += t
                    vsum += v
                    n += 1
    # Finds average time & voltage arrays
    t_avg = tsum / n
    v_avg = vsum / n

    # Plots average waveform & saves image
    plt.plot(t_avg, v_avg)
    plt.xlabel('Time (s)')
    plt.ylabel('Normalized Voltage')
    plt.title('Average Waveform')
    plt.savefig(save_file / 'avg_waveform.png', dpi=360)

    # Saves average waveform data
    file_name = dest_path / 'hist_data' / 'avg_waveform.txt'
    hdr = 'Average Waveform\n\n\n\nTime,Ampl'
    ww(t_avg, v_avg, file_name, hdr)
