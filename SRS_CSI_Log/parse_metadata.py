#!/usr/bin/env python3
"""
SRS CSI Session Metadata Parser
Analyzes session_metadata.jsonl to track UE sessions and files

Usage:
    python3 parse_metadata.py
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_metadata(metadata_file='session_metadata.jsonl'):
    """Parse the session metadata file"""
    
    if not Path(metadata_file).exists():
        print(f"Metadata file not found: {metadata_file}")
        print("Run the gNB with SRS CSI collection enabled first.")
        return None
    
    sessions = defaultdict(list)
    
    with open(metadata_file, 'r') as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                rnti = entry['rnti']
                sessions[rnti].append(entry)
    
    return sessions

def print_summary(sessions):
    """Print summary of all sessions"""
    
    print("="*70)
    print("SRS CSI SESSION SUMMARY")
    print("="*70)
    print(f"\nTotal UEs (RNTIs): {len(sessions)}")
    print(f"Total events: {sum(len(events) for events in sessions.values())}")
    
    print("\n" + "="*70)
    print("PER-UE SESSION DETAILS")
    print("="*70)
    
    for rnti in sorted(sessions.keys()):
        events = sessions[rnti]
        
        print(f"\n📡 RNTI: {rnti} (0x{rnti:04X})")
        print(f"   Events: {len(events)}")
        
        # Find session start and latest event
        start_event = next((e for e in events if e['event'] == 'session_start'), None)
        if start_event:
            print(f"   Session Start: {start_event['timestamp']}")
            print(f"   Initial File: {start_event['file']}")
        
        # Count file rotations
        rotations = [e for e in events if e['event'] == 'file_rotation']
        if rotations:
            print(f"   File Rotations: {len(rotations)}")
            print(f"   Latest File: {rotations[-1]['file']}")
        
        # List all files for this RNTI
        files = [e['file'] for e in events if 'file' in e]
        unique_files = sorted(set(files))
        print(f"   Total Files: {len(unique_files)}")
        for i, f in enumerate(unique_files, 1):
            print(f"      {i}. {f}")

def find_ue_files(sessions, rnti):
    """Get all files for a specific RNTI"""
    
    if rnti not in sessions:
        print(f"RNTI {rnti} not found in metadata")
        return []
    
    files = []
    for event in sessions[rnti]:
        if 'file' in event:
            files.append(event['file'])
    
    return sorted(set(files))

def export_ue_session_list(sessions, output_file='ue_sessions.json'):
    """Export structured session information"""
    
    session_list = []
    
    for rnti, events in sessions.items():
        # Build session info
        start_event = next((e for e in events if e['event'] == 'session_start'), None)
        
        files = sorted(set(e['file'] for e in events if 'file' in e))
        
        session_info = {
            'rnti': rnti,
            'rnti_hex': f"0x{rnti:04X}",
            'session_start': start_event['timestamp'] if start_event else None,
            'num_files': len(files),
            'files': files,
            'num_events': len(events)
        }
        
        session_list.append(session_info)
    
    # Sort by session start time
    session_list.sort(key=lambda x: x['session_start'] if x['session_start'] else '')
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump(session_list, f, indent=2)
    
    print(f"\n✓ Session list exported to: {output_file}")

def main():
    metadata_file = Path(__file__).parent / 'session_metadata.jsonl'
    
    print(f"Parsing metadata from: {metadata_file}\n")
    
    sessions = parse_metadata(metadata_file)
    
    if not sessions:
        return
    
    # Print summary
    print_summary(sessions)
    
    # Export structured data
    output_file = Path(__file__).parent / 'ue_sessions.json'
    export_ue_session_list(sessions, output_file)
    
    # Example: Filter files for specific RNTI
    print("\n" + "="*70)
    print("EXAMPLE USAGE")
    print("="*70)
    print("\n# Get files for specific RNTI in Python:")
    print("import json")
    print("sessions = json.load(open('ue_sessions.json'))")
    print("ue1_files = [s['files'] for s in sessions if s['rnti'] == 17921]")
    print("print(ue1_files)")
    
    print("\n# Load CSI data for specific UE:")
    print("import pandas as pd")
    print("ue1_data = pd.concat([pd.read_csv(f.replace('.bin', '.csv')) ")
    print("                      for f in ue1_files[0]])")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    main()
