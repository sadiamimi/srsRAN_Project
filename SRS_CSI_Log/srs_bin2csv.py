#!/usr/bin/env python3
"""
SRS CSI Binary to CSV Converter
Converts binary SRS CSI log files to human-readable CSV format.

Binary Format (per entry):
- Header (14 bytes):
  - timestamp_us (8 bytes, uint64): Microseconds since epoch
  - rx_port (2 bytes, uint16): Receive antenna port
  - tx_port (2 bytes, uint16): Transmit antenna port (UE)
  - num_tones (2 bytes, uint16): Number of SRS tones in this entry
- Samples (12 bytes each, repeated num_tones times):
  - subcarrier_index (2 bytes, uint16): Subcarrier/tone index
  - symbol_index (2 bytes, uint16): OFDM symbol index
  - real (4 bytes, float): Real part of H(k)
  - imag (4 bytes, float): Imaginary part of H(k)

Usage:
    python3 srs_bin2csv.py <binary_file.bin>
"""

import struct
import sys
import os
from datetime import datetime
import math

def read_srs_entry(f):
    """Read one SRS CSI entry from binary file."""
    # Read header (14 bytes)
    header_data = f.read(14)
    if len(header_data) < 14:
        return None
    
    timestamp_us, rx_port, tx_port, num_tones = struct.unpack('<QHHH', header_data)
    
    # Sanity check: num_tones should be reasonable (0-3276 max for 20MHz BW)
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

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 srs_bin2csv.py <binary_file.bin>")
        print("\nExample:")
        print("  python3 srs_bin2csv.py srs_csi_20260108_203000_1.bin")
        sys.exit(1)
    
    input_filename = sys.argv[1]
    if not os.path.exists(input_filename):
        print(f"Error: File '{input_filename}' not found")
        sys.exit(1)
    
    # Generate output filename
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}.csv"
    
    print(f"Converting SRS CSI binary file...")
    print(f"  Input:  {input_filename}")
    print(f"  Output: {output_filename}")
    print()
    
    entry_count = 0
    total_samples = 0
    
    try:
        with open(input_filename, 'rb') as infile, open(output_filename, 'w') as outfile:
            # Write CSV header
            outfile.write("entry_num,timestamp_us,timestamp_readable,rx_port,tx_port,num_tones,")
            outfile.write("subcarrier,symbol,real,imag,magnitude,phase_deg\n")
            
            while True:
                entry = read_srs_entry(infile)
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
