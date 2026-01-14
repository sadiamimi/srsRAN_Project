#!/usr/bin/env python3
"""
SRS CSI Binary to CSV Converter
Converts binary SRS CSI log files to human-readable CSV format.

Supports two modes:
- Mode 1 (Multi-UE): 16-byte header with RNTI (srs_csi_rnti_*.bin)
- Mode 2 (Single UE): 14-byte header without RNTI (srs_csi_*.bin)

Mode 1 Binary Format (per entry):
- Header (16 bytes):
  - timestamp_us (8 bytes, uint64): Microseconds since epoch
  - rnti (2 bytes, uint16): UE Radio Network Temporary Identifier  
  - rx_port (2 bytes, uint16): Receive antenna port
  - tx_port (2 bytes, uint16): Transmit antenna port (UE)
  - num_tones (2 bytes, uint16): Number of SRS tones in this entry
- Samples (12 bytes each, repeated num_tones times):
  - subcarrier_index (2 bytes, uint16): Subcarrier/tone index
  - symbol_index (2 bytes, uint16): OFDM symbol index
  - real (4 bytes, float): Real part of H(k)
  - imag (4 bytes, float): Imaginary part of H(k)

Mode 2 Binary Format (per entry):
- Header (14 bytes - NO RNTI):
  - timestamp_us (8 bytes, uint64): Microseconds since epoch
  - rx_port (2 bytes, uint16): Receive antenna port
  - tx_port (2 bytes, uint16): Transmit antenna port (UE)
  - num_tones (2 bytes, uint16): Number of SRS tones in this entry
- Samples: Same as Mode 1

Usage:
    python3 srs_bin2csv.py <binary_file.bin> [--mode {1|2}]
    
    If --mode is not specified, it's auto-detected from filename:
    - Files matching 'srs_csi_rnti_*' use Mode 1
    - Files matching 'srs_csi_*' (without rnti) use Mode 2
"""

import struct
import sys
import os
from datetime import datetime
import math
import argparse

import argparse

def read_srs_entry_mode1(f):
    """Read one SRS CSI entry from binary file (Mode 1 - with RNTI)."""
    # Read header (16 bytes)
    header_data = f.read(16)
    if len(header_data) < 16:
        return None
    
    timestamp_us, rnti, rx_port, tx_port, num_tones = struct.unpack('<QHHHH', header_data)
    
    # Sanity check: num_tones should be reasonable (0-3276 max for 20MHz BW)
    if num_tones > 10000 or num_tones == 0:
        print(f"Warning: Suspicious num_tones={num_tones} at file position {f.tell()-16}")
        return None
    
    # Read samples (12 bytes each)
    samples = []
    for _ in range(num_tones):
        sample_data = f.read(12)
        if len(sample_data) < 12:
            print(f"Warning: Incomplete sample data (expected {num_tones} tones, got {len(samples)})")
            break
            
        subcarrier_idx, symbol_idx, real_part, imag_part = struct.unpack('<HHff', sample_data)
        samples.append((subcarrier_idx, symbol_idx, real_part, imag_part))
    
    if len(samples) == 0:
        return None
    
    return {
        'timestamp_us': timestamp_us,
        'rnti': rnti,
        'rx_port': rx_port,
        'tx_port': tx_port,
        'num_tones': num_tones,
        'samples': samples
    }

def read_srs_entry_mode2(f):
    """Read one SRS CSI entry from binary file (Mode 2 - NO RNTI)."""
    # Read header (14 bytes - no RNTI field)
    header_data = f.read(14)
    if len(header_data) < 14:
        return None
    
    timestamp_us, rx_port, tx_port, num_tones = struct.unpack('<QHHH', header_data)
    
    # Sanity check: num_tones should be reasonable
    if num_tones > 10000 or num_tones == 0:
        print(f"Warning: Suspicious num_tones={num_tones} at file position {f.tell()-14}")
        return None
    
    # Read samples (12 bytes each)
    samples = []
    for _ in range(num_tones):
        sample_data = f.read(12)
        if len(sample_data) < 12:
            print(f"Warning: Incomplete sample data (expected {num_tones} tones, got {len(samples)})")
            break
            
        subcarrier_idx, symbol_idx, real_part, imag_part = struct.unpack('<HHff', sample_data)
        samples.append((subcarrier_idx, symbol_idx, real_part, imag_part))
    
    if len(samples) == 0:
        return None
    
    return {
        'timestamp_us': timestamp_us,
        'rnti': None,  # No RNTI in Mode 2
        'rx_port': rx_port,
        'tx_port': tx_port,
        'num_tones': num_tones,
        'samples': samples
    }

def read_srs_entry(f):
    """Read one SRS CSI entry from binary file."""
    # Read header (16 bytes)
    header_data = f.read(16)
    if len(header_data) < 16:
        return None
    
    timestamp_us, rnti, rx_port, tx_port, num_tones = struct.unpack('<QHHHH', header_data)
    
    # Sanity check: num_tones should be reasonable (0-3276 max for 20MHz BW)
    if num_tones > 10000 or num_tones == 0:
        print(f"Warning: Suspicious num_tones={num_tones} at file position {f.tell()-16}")
        return None
    
    # Read samples (12 bytes each)
    samples = []
    for _ in range(num_tones):
        sample_data = f.read(12)
        if len(sample_data) < 12:
            print(f"Warning: Incomplete sample data (expected {num_tones} tones, got {len(samples)})")
            break
            
        subcarrier_idx, symbol_idx, real_part, imag_part = struct.unpack('<HHff', sample_data)
        samples.append((subcarrier_idx, symbol_idx, real_part, imag_part))
    
    if len(samples) == 0:
        return None
    
    return {
        'timestamp_us': timestamp_us,
        'rnti': rnti,
        'rx_port': rx_port,
        'tx_port': tx_port,
        'num_tones': num_tones,
        'samples': samples
    }

def timestamp_to_readable(timestamp_us):
    """Convert microsecond timestamp to readable format."""
    timestamp_s = timestamp_us / 1_000_000.0
    dt = datetime.fromtimestamp(timestamp_s)
    microseconds = timestamp_us % 1_000_000
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{microseconds:06d}"

def detect_mode_from_filename(filename):
    """Auto-detect mode from filename pattern."""
    basename = os.path.basename(filename)
    if 'rnti' in basename:
        return 1
    else:
        return 2

def main():
    parser = argparse.ArgumentParser(
        description='Convert SRS CSI binary files to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 srs_bin2csv.py srs_csi_20260114_143000_1.bin
  python3 srs_bin2csv.py srs_csi_rnti_0x4601_20260114_143000_1.bin
  python3 srs_bin2csv.py my_file.bin --mode 2
        """
    )
    parser.add_argument('input_file', help='Input binary file')
    parser.add_argument('--mode', type=int, choices=[1, 2], 
                       help='Collection mode (1=Multi-UE with RNTI, 2=Single UE). Auto-detected if not specified.')
    
    args = parser.parse_args()
    
    input_filename = args.input_file
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found")
        sys.exit(1)
    
    # Determine mode
    if args.mode:
        mode = args.mode
        print(f"Using specified mode: {mode}")
    else:
        mode = detect_mode_from_filename(input_filename)
        print(f"Auto-detected mode: {mode} ({'Multi-UE' if mode == 1 else 'Single UE'})")
    
    # Select appropriate reader function
    if mode == 1:
        read_entry_func = read_srs_entry_mode1
        header_info = "16-byte header with RNTI"
    else:
        read_entry_func = read_srs_entry_mode2
        header_info = "14-byte header (no RNTI)"
    
    # Generate output filename
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}.csv"
    
    print(f"Converting SRS CSI binary file...")
    print(f"  Input:  {input_filename}")
    print(f"  Output: {output_filename}")
    print(f"  Format: Mode {mode} ({header_info})")
    print()
    
    entry_count = 0
    total_samples = 0
    
    try:
        with open(input_filename, 'rb') as infile, open(output_filename, 'w') as outfile:
            # Write CSV header
            if mode == 1:
                outfile.write("entry_num,timestamp_us,timestamp_readable,rnti,rx_port,tx_port,num_tones,")
            else:
                outfile.write("entry_num,timestamp_us,timestamp_readable,rx_port,tx_port,num_tones,")
            outfile.write("subcarrier,symbol,real,imag,magnitude,phase_deg\n")
            
            while True:
                entry = read_entry_func(infile)
                if entry is None:
                    break
                
                entry_count += 1
                timestamp_readable = timestamp_to_readable(entry['timestamp_us'])
                
                # Write all samples for this SRS occasion
                for sample in entry['samples']:
                    subcarrier_idx, symbol_idx, real_part, imag_part = sample
                    magnitude = math.sqrt(real_part**2 + imag_part**2)
                    phase_deg = math.degrees(math.atan2(imag_part, real_part))
                    
                    outfile.write(f"{entry_count},{entry['timestamp_us']},{timestamp_readable},")
                    if mode == 1:
                        outfile.write(f"{entry['rnti']},")
                    outfile.write(f"{entry['rx_port']},{entry['tx_port']},{entry['num_tones']},")
                    outfile.write(f"{subcarrier_idx},{symbol_idx},")
                    outfile.write(f"{real_part:.6f},{imag_part:.6f},{magnitude:.6f},{phase_deg:.2f}\n")
                    
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
