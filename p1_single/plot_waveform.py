from p1_functions import *


# Plots a waveform for the user to view (does not save)
def plot_waveform(start, end, fil_band, version, folder):
    for i in range(start, end + 1):
        if version == 'd0':
            show_waveform(Path(r'/Volumes/TOSHIBA EXT/data/watchman/20190513_watchman_spe/waveforms/' + str(fil_band) +
                               r'/d0/C2--waveforms--%05d.txt' % i), version)
        elif version == 'd1':
            show_waveform(Path(r'/Volumes/TOSHIBA EXT/data/watchman/20190513_watchman_spe/waveforms/' + str(fil_band) +
                               '/d1/' + str(folder) + r'/D1--waveforms--%05d.txt' % i), version)
        else:
            print('Invalid version of data (must be d0 or d1)')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog="p1", description="Creating D1")
    parser.add_argument("--start", type=int, help='first file number to plot', default=0)
    parser.add_argument("--end", type=int, help='last file number to plot', default=0)
    parser.add_argument("--fil_band", type=str, help='folder name for data', default='full_bdw_no_nf')
    parser.add_argument("--version", type=str, help='d0 or d1', default='d0')
    parser.add_argument("--folder", type=str, help='if d1, folder within d1', default=' ')
    args = parser.parse_args()

    plot_waveform(args.start, args.end, args.fil_band, args.version, args.folder)
