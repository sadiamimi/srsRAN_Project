# SRS CSI Data Collection

This directory contains SRS (Sounding Reference Signal) Channel State Information collected from the gNB.

## Binary File Format

Each `.bin` file contains sequential SRS CSI entries with the following structure:

### Per Entry (14-byte header + N × 12-byte samples):
- **Header (14 bytes)**:
  - `timestamp_us` (8 bytes, uint64): Microseconds since epoch
  - `rx_port` (2 bytes, uint16): Receive antenna port at gNB
  - `tx_port` (2 bytes, uint16): Transmit antenna port at UE
  - `num_tones` (2 bytes, uint16): Number of SRS tones/subcarriers in this entry
  
- **Samples (12 bytes each, repeated `num_tones` times)**:
  - `subcarrier_index` (2 bytes, uint16): Subcarrier/tone index
  - `symbol_index` (2 bytes, uint16): OFDM symbol index
  - `real` (4 bytes, float32): Real part of channel estimate H(k)
  - `imag` (4 bytes, float32): Imaginary part of channel estimate H(k)

## File Rotation

- Files are automatically rotated when they reach **100 MB**
- Naming: `srs_csi_YYYYMMDD_HHMMSS_N.bin` (N = sequence number)
- Example: `srs_csi_20260108_204150_1.bin`, `_2.bin`, etc.

## Typical Data Characteristics

Based on collected data:
- **SRS comb spacing**: 4 subcarriers (e.g., 12, 16, 20, 24, ...)
- **OFDM symbol**: Typically symbol 13 in the slot
- **Tones per occasion**: 144 for standard allocation in 20MHz BW
- **Magnitude range**: ~0.1 to 0.3 (varies with channel conditions)
- **Entry size**: 14 + (144 × 12) = 1,742 bytes per SRS occasion

## Data Collection Rate

Based on actual measurements with 40ms SRS period and 20MHz BW:
- **SRS occasions**: 25 per second (1000ms / 40ms)
- **Tones per occasion**: ~144 (typical allocation, depends on UE RB configuration)
- **File size growth**: ~3.5 KB per occasion, ~87 KB/sec
- **Time to 100MB**: ~19-20 minutes per file

## Converting to CSV

Use the provided Python script to convert binary files to CSV:

```bash
# Basic usage
python3 srs_bin2csv.py srs_csi_20260108_203045_1.bin

# Or if executable
./srs_bin2csv.py srs_csi_20260108_203045_1.bin
```

### CSV Output Format

The script generates a CSV file with columns:
- `entry_num`: Sequential SRS occasion number
- `timestamp_us`: Microsecond timestamp
- `timestamp_readable`: Human-readable timestamp
- `rx_port`: Receive antenna port
- `tx_port`: Transmit antenna port
- `num_tones`: Number of tones in this occasion
- `subcarrier`: Subcarrier index
- `symbol`: OFDM symbol index
- `real`: Real part of H(k)
- `imag`: Imaginary part of H(k)
- `magnitude`: |H(k)| = sqrt(real² + imag²)
- `phase_deg`: ∠H(k) in degrees

### Example

```bash
# Convert binary to CSV
python3 srs_bin2csv.py srs_csi_20260108_203045_1.bin

# Output: srs_csi_20260108_203045_1.csv
# Can be opened in Excel, pandas, MATLAB, etc.
```

## Data Analysis Examples

### Python (pandas)
```python
import pandas as pd
import numpy as np

# Load CSV
df = pd.read_csv('srs_csi_20260108_203045_1.csv')

# Group by SRS occasion
for entry_num, group in df.groupby('entry_num'):
    # Extract per-tone CSI
    subcarriers = group['subcarrier'].values
    H_real = group['real'].values
    H_imag = group['imag'].values
    H = H_real + 1j * H_imag
    
    # Your analysis here
    print(f"Entry {entry_num}: {len(H)} tones, avg magnitude: {np.abs(H).mean():.3f}")
```

### MATLAB
```matlab
% Load CSV
data = readtable('srs_csi_20260108_203045_1.csv');

% Extract first SRS occasion
entry1 = data(data.entry_num == 1, :);
H = entry1.real + 1j * entry1.imag;

% Plot frequency response
plot(entry1.subcarrier, abs(H));
xlabel('Subcarrier Index');
ylabel('|H(k)|');
title('SRS Channel Frequency Response');
```

## Notes

- **Collection Point**: After timing advance and phase compensation, before frequency averaging
- **Signal Processing**: Captures aligned per-tone CSI H(k) preserving frequency selectivity
- **UE Requirement**: SRS is only transmitted when UE is RRC-connected to the gNB
- **Configuration**: 40ms SRS period set in `/var/tmp/etc/srsran/gnb_rf_x310_ho.yml`
- **Storage Location**: `/var/tmp/srsRAN_Project/SRS_CSI_Log/`
- **Implementation**: Modified `lib/phy/upper/signal_processors/srs/srs_estimator_generic_impl.cpp`
