#!/usr/bin/env python3
"""
SRS CSI MODE 4 Binary to CSV Converter
Converts MODE 4 binary SRS CSI log files (with X[k], Y[k], H_raw[k], H_comp[k]) to CSV.

MODE 4 Binary Format (per entry):
- Header (46 bytes, current):
  - timestamp_us (8 bytes, uint64): Microseconds since epoch
  - rx_port (2 bytes, uint16): Receive antenna port
  - tx_port (2 bytes, uint16): Transmit antenna port (UE)
  - rnti (2 bytes, uint16): UE RNTI (0 if unavailable)
  - num_tones (2 bytes, uint16): Number of SRS tones in this entry
  - time_alignment (8 bytes, double): Time alignment in seconds
  - scs_khz (4 bytes, float): Subcarrier spacing in kHz
  - comb_size (2 bytes, uint16): SRS comb size (2 or 4)
  - k0 (2 bytes, uint16): Initial subcarrier index
  - start_symbol (2 bytes, uint16): Starting OFDM symbol index
  - rsrp_linear (4 bytes, float): Reference Signal Received Power (linear)
  - noise_variance (4 bytes, float): Noise variance
  - snr_db (4 bytes, float): Signal-to-Noise Ratio in dB

- Samples (36 bytes each, repeated num_tones times):
  - subcarrier_index (2 bytes, uint16): Subcarrier/tone index
  - symbol_index (2 bytes, uint16): OFDM symbol index
  - x_real (4 bytes, float): Transmitted sequence X[k] - real part
  - x_imag (4 bytes, float): Transmitted sequence X[k] - imaginary part
  - y_real (4 bytes, float): Received signal Y[k] - real part
  - y_imag (4 bytes, float): Received signal Y[k] - imaginary part
  - h_raw_real (4 bytes, float): Raw channel H[k] before compensation - real
  - h_raw_imag (4 bytes, float): Raw channel H[k] before compensation - imag
  - h_comp_real (4 bytes, float): Compensated channel H[k] - real part
  - h_comp_imag (4 bytes, float): Compensated channel H[k] - imag part

Usage:
    python3 srs_mode4_bin2csv.py <binary_file.bin>
    
Example:
    python3 srs_mode4_bin2csv.py srs_csi_full_20260205_143000_1.bin
"""

import struct
import sys
import os
from datetime import datetime
import math
import argparse

def read_srs_mode4_entry(f, header_bytes):
    """Read one SRS CSI MODE 4 entry from binary file."""
    if header_bytes == 46:
        # Read header (46 bytes): includes RNTI
        header_data = f.read(46)
        if len(header_data) < 46:
            return None

        # <Q = uint64, H = uint16, d = double, f = float
        timestamp_us, rx_port, tx_port, rnti, num_tones, time_alignment, scs_khz, \
        comb_size, k0, start_symbol, rsrp_linear, noise_variance, snr_db = \
            struct.unpack('<QHHHHdfHHHfff', header_data)
    elif header_bytes == 44:
        # Legacy header (44 bytes): no RNTI field
        header_data = f.read(44)
        if len(header_data) < 44:
            return None

        timestamp_us, rx_port, tx_port, num_tones, time_alignment, scs_khz, \
        comb_size, k0, start_symbol, rsrp_linear, noise_variance, snr_db = \
            struct.unpack('<QHHHdfHHHfff', header_data)
        rnti = 0
    else:
        raise ValueError(f"Unsupported header_bytes={header_bytes}")
    
    # Sanity check: num_tones should be reasonable
    if num_tones > 10000 or num_tones == 0:
        print(f"Warning: Suspicious num_tones={num_tones} at file position {f.tell()-header_bytes}")
        return None
    
    # Read samples (36 bytes each)
    samples = []
    for _ in range(num_tones):
        sample_data = f.read(36)
        if len(sample_data) < 36:
            print(f"Warning: Incomplete sample data (expected {num_tones} tones, got {len(samples)})")
            break
            
        # Unpack: subcarrier(H), symbol(H), X_re(f), X_im(f), Y_re(f), Y_im(f), 
        #         H_raw_re(f), H_raw_im(f), H_comp_re(f), H_comp_im(f)
        subcarrier_idx, symbol_idx, x_real, x_imag, y_real, y_imag, \
        h_raw_real, h_raw_imag, h_comp_real, h_comp_imag = \
            struct.unpack('<HHffffffff', sample_data)
        
        samples.append({
            'subcarrier': subcarrier_idx,
            'symbol': symbol_idx,
            'x_real': x_real,
            'x_imag': x_imag,
            'y_real': y_real,
            'y_imag': y_imag,
            'h_raw_real': h_raw_real,
            'h_raw_imag': h_raw_imag,
            'h_comp_real': h_comp_real,
            'h_comp_imag': h_comp_imag
        })
    
    if len(samples) == 0:
        return None
    
    return {
        'timestamp_us': timestamp_us,
        'rx_port': rx_port,
        'tx_port': tx_port,
        'rnti': rnti,
        'num_tones': num_tones,
        'time_alignment': time_alignment,
        'scs_khz': scs_khz,
        'comb_size': comb_size,
        'k0': k0,
        'start_symbol': start_symbol,
        'rsrp_linear': rsrp_linear,
        'noise_variance': noise_variance,
        'snr_db': snr_db,
        'samples': samples
    }

def timestamp_to_readable(timestamp_us):
    """Convert microsecond timestamp to readable format."""
    timestamp_s = timestamp_us / 1_000_000.0
    dt = datetime.fromtimestamp(timestamp_s)
    microseconds = timestamp_us % 1_000_000
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{microseconds:06d}"

def main():
    parser = argparse.ArgumentParser(
        description='Convert SRS CSI MODE 4 binary files to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python3 srs_mode4_bin2csv.py srs_csi_full_20260205_143000_1.bin
        """
    )
    parser.add_argument('input_file', help='Input binary file (MODE 4 format)')
    parser.add_argument(
        '--header-bytes',
        type=int,
        choices=[44, 46],
        default=46,
        help='MODE 4 header size (44 = legacy without RNTI, 46 = current with RNTI)',
    )
    
    args = parser.parse_args()
    
    input_filename = args.input_file
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found")
        sys.exit(1)
    
    # Generate output filename
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}.csv"
    
    print(f"Converting SRS CSI MODE 4 binary file...")
    print(f"  Input:  {input_filename}")
    print(f"  Output: {output_filename}")
    print(f"  Format: MODE 4 ({args.header_bytes}-byte header + 36-byte samples)")
    print()
    
    entry_count = 0
    total_samples = 0
    
    try:
        with open(input_filename, 'rb') as infile, open(output_filename, 'w') as outfile:
            # Write CSV header
            outfile.write("entry_num,timestamp_us,timestamp_readable,rx_port,tx_port,rnti,num_tones,")
            outfile.write("time_alignment_sec,scs_khz,comb_size,k0,start_symbol,")
            outfile.write("rsrp_linear,rsrp_dbm,noise_variance,snr_db,")
            outfile.write("subcarrier,symbol,")
            outfile.write("x_real,x_imag,x_mag,x_phase_deg,")
            outfile.write("y_real,y_imag,y_mag,y_phase_deg,")
            outfile.write("h_raw_real,h_raw_imag,h_raw_mag,h_raw_phase_deg,")
            outfile.write("h_comp_real,h_comp_imag,h_comp_mag,h_comp_phase_deg\n")
            
            while True:
                entry = read_srs_mode4_entry(infile, args.header_bytes)
                if entry is None:
                    break
                
                entry_count += 1
                timestamp_readable = timestamp_to_readable(entry['timestamp_us'])
                
                # Convert RSRP to dBm (assuming 1mW reference)
                # RSRP_dBm = 10*log10(RSRP_linear / 1mW)
                # For 0-reference (no mW conversion): RSRP_dB = 10*log10(RSRP_linear)
                if entry['rsrp_linear'] > 0:
                    rsrp_dbm = 10 * math.log10(entry['rsrp_linear'])
                else:
                    rsrp_dbm = float('-inf')
                
                # Write all samples for this SRS occasion
                for sample in entry['samples']:
                    # Calculate magnitudes and phases for X[k]
                    x_mag = math.sqrt(sample['x_real']**2 + sample['x_imag']**2)
                    x_phase_deg = math.degrees(math.atan2(sample['x_imag'], sample['x_real']))
                    
                    # Calculate magnitudes and phases for Y[k]
                    y_mag = math.sqrt(sample['y_real']**2 + sample['y_imag']**2)
                    y_phase_deg = math.degrees(math.atan2(sample['y_imag'], sample['y_real']))
                    
                    # Calculate magnitudes and phases for H_raw[k]
                    h_raw_mag = math.sqrt(sample['h_raw_real']**2 + sample['h_raw_imag']**2)
                    h_raw_phase_deg = math.degrees(math.atan2(sample['h_raw_imag'], sample['h_raw_real']))
                    
                    # Calculate magnitudes and phases for H_comp[k]
                    h_comp_mag = math.sqrt(sample['h_comp_real']**2 + sample['h_comp_imag']**2)
                    h_comp_phase_deg = math.degrees(math.atan2(sample['h_comp_imag'], sample['h_comp_real']))
                    
                    # Write entry header info
                    outfile.write(f"{entry_count},{entry['timestamp_us']},{timestamp_readable},")
                    outfile.write(f"{entry['rx_port']},{entry['tx_port']},{entry['rnti']},{entry['num_tones']},")
                    outfile.write(f"{entry['time_alignment']:.9e},{entry['scs_khz']:.1f},")
                    outfile.write(f"{entry['comb_size']},{entry['k0']},{entry['start_symbol']},")
                    outfile.write(f"{entry['rsrp_linear']:.6e},{rsrp_dbm:.2f},")
                    outfile.write(f"{entry['noise_variance']:.6e},{entry['snr_db']:.2f},")
                    
                    # Write sample info
                    outfile.write(f"{sample['subcarrier']},{sample['symbol']},")
                    
                    # X[k]
                    outfile.write(f"{sample['x_real']:.6f},{sample['x_imag']:.6f},")
                    outfile.write(f"{x_mag:.6f},{x_phase_deg:.2f},")
                    
                    # Y[k]
                    outfile.write(f"{sample['y_real']:.6f},{sample['y_imag']:.6f},")
                    outfile.write(f"{y_mag:.6f},{y_phase_deg:.2f},")
                    
                    # H_raw[k]
                    outfile.write(f"{sample['h_raw_real']:.6f},{sample['h_raw_imag']:.6f},")
                    outfile.write(f"{h_raw_mag:.6f},{h_raw_phase_deg:.2f},")
                    
                    # H_comp[k]
                    outfile.write(f"{sample['h_comp_real']:.6f},{sample['h_comp_imag']:.6f},")
                    outfile.write(f"{h_comp_mag:.6f},{h_comp_phase_deg:.2f}\n")
                    
                    total_samples += 1
                
                if entry_count % 100 == 0:
                    print(f"  Processed {entry_count} SRS occasions, {total_samples} tones...")
        
        print(f"\n✓ Conversion complete!")
        print(f"  Total SRS occasions: {entry_count}")
        print(f"  Total CSI samples: {total_samples}")
        if entry_count > 0:
            print(f"  Average tones/occasion: {total_samples/entry_count:.1f}")
        
        # Get file sizes
        input_size = os.path.getsize(input_filename)
        output_size = os.path.getsize(output_filename)
        print(f"\n  Input size:  {input_size:,} bytes ({input_size/1024/1024:.2f} MB)")
        print(f"  Output size: {output_size:,} bytes ({output_size/1024/1024:.2f} MB)")
        
    except Exception as e:
        print(f"\n✗ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()