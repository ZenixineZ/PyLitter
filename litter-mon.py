#!/usr/bin/env python3
"""
Raspberry Pi Webcam Recorder
Records video from webcam to configurable location with customizable settings
Automatically splits recordings into 5-minute chunks
"""

import cv2
import argparse
import os
from datetime import datetime
import time

def setup_camera(width, height, fps, camera_index):
    """Initialize camera with settings"""
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        raise Exception(f"Cannot open camera {camera_index}")
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    
    # Verify settings
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Camera initialized:")
    print(f"  Resolution: {actual_width}x{actual_height}")
    print(f"  FPS: {actual_fps}")
    
    return cap

def get_fourcc(codec_name):
    """Get FourCC code for codec"""
    codec_map = {
        "H264": cv2.VideoWriter_fourcc(*'H264'),
        "MJPG": cv2.VideoWriter_fourcc(*'MJPG'),
        "XVID": cv2.VideoWriter_fourcc(*'XVID'),
        "MP4V": cv2.VideoWriter_fourcc(*'mp4v'),
    }
    return codec_map.get(codec_name, cv2.VideoWriter_fourcc(*'H264'))

def create_video_writer(output_dir, width, height, fps, codec, file_format, chunk_number=None):
    """Create a new video writer with timestamped filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if chunk_number is not None:
        filename = f"recording_{timestamp}_part{chunk_number:03d}.{file_format}"
    else:
        filename = f"recording_{timestamp}.{file_format}"
    
    filepath = os.path.join(output_dir, filename)
    
    fourcc = get_fourcc(codec)
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise Exception(f"Failed to initialize video writer for {filepath}")
    
    return out, filepath

def record_video(output_dir, width, height, fps, codec, file_format, camera_index, 
                duration=None, headless=False, chunk_duration=300):
    """
    Record video with given configuration, splitting into chunks
    
    Args:
        chunk_duration: Duration of each chunk in seconds (default: 300 = 5 minutes)
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize camera first
    cap = setup_camera(width, height, fps, camera_index)
    
    # Get actual resolution
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if actual_width != width or actual_height != height:
        print(f"  Note: Camera provided {actual_width}x{actual_height} instead of requested {width}x{height}")
    
    # Measure actual FPS by capturing test frames
    print("  Measuring actual camera frame rate...")
    test_frames = 60
    start_time = time.time()
    for _ in range(test_frames):
        ret, _ = cap.read()
        if not ret:
            break
    elapsed = time.time() - start_time
    measured_fps = test_frames / elapsed if elapsed > 0 else fps
    
    print(f"  Measured FPS: {measured_fps:.1f}")
    
    print(f"\nRecording will be split into {chunk_duration//60} minute chunks")
    print(f"Press 'q' to stop recording")
    if duration:
        print(f"Total recording duration: {duration} seconds")
    
    frame_count = 0
    chunk_number = 1
    chunk_frame_count = 0
    total_start_time = datetime.now()
    chunk_start_time = datetime.now()
    
    # Create first video writer
    out, current_filepath = create_video_writer(
        output_dir, actual_width, actual_height, measured_fps, 
        codec, file_format, chunk_number
    )
    print(f"\nChunk {chunk_number}: {current_filepath}")
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("Failed to capture frame")
                break
            
            # Add timestamp overlay to frame
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_thickness = 2
            text_color = (255, 255, 255)  # White
            bg_color = (0, 0, 0)  # Black background
            
            # Get text size for background rectangle
            (text_width, text_height), baseline = cv2.getTextSize(
                current_time, font, font_scale, font_thickness
            )
            
            # Draw black background rectangle
            cv2.rectangle(
                frame,
                (10, frame.shape[0] - text_height - baseline - 10),
                (10 + text_width + 10, frame.shape[0] - 5),
                bg_color,
                -1  # Filled rectangle
            )
            
            # Draw timestamp text
            cv2.putText(
                frame,
                current_time,
                (15, frame.shape[0] - baseline - 8),
                font,
                font_scale,
                text_color,
                font_thickness,
                cv2.LINE_AA
            )
            
            # Write frame to current video file
            out.write(frame)
            frame_count += 1
            chunk_frame_count += 1
            
            # Show preview unless headless
            if not headless:
                cv2.imshow('Recording (press q to stop)', frame)
            
            # Check for quit (only if showing preview)
            if not headless and cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Check if chunk duration reached
            chunk_elapsed = (datetime.now() - chunk_start_time).total_seconds()
            if chunk_elapsed >= chunk_duration:
                # Close current video writer
                chunk_duration_actual = (datetime.now() - chunk_start_time).total_seconds()
                print(f"\nChunk {chunk_number} complete:")
                print(f"  Duration: {chunk_duration_actual:.1f}s")
                print(f"  Frames: {chunk_frame_count}")
                print(f"  File: {current_filepath}")
                
                out.release()
                
                # Check if total duration is specified and reached
                total_elapsed = (datetime.now() - total_start_time).total_seconds()
                if duration and total_elapsed >= duration:
                    break
                
                # Create new video writer for next chunk
                chunk_number += 1
                chunk_frame_count = 0
                chunk_start_time = datetime.now()
                
                out, current_filepath = create_video_writer(
                    output_dir, actual_width, actual_height, measured_fps, 
                    codec, file_format, chunk_number
                )
                print(f"\nChunk {chunk_number}: {current_filepath}")
            
            # Check total duration limit
            if duration:
                total_elapsed = (datetime.now() - total_start_time).total_seconds()
                if total_elapsed >= duration:
                    break
            
            # Print progress every 30 frames
            if frame_count % 30 == 0:
                total_elapsed = (datetime.now() - total_start_time).total_seconds()
                chunk_elapsed = (datetime.now() - chunk_start_time).total_seconds()
                chunk_remaining = chunk_duration - chunk_elapsed
                print(f"Chunk {chunk_number}: {chunk_frame_count} frames, "
                      f"{chunk_elapsed:.1f}s/{chunk_duration}s "
                      f"({chunk_remaining:.0f}s remaining) | "
                      f"Total: {frame_count} frames, {total_elapsed:.1f}s", end='\r')
    
    except KeyboardInterrupt:
        print("\n\nRecording interrupted by user")
    
    finally:
        # Cleanup
        total_elapsed = (datetime.now() - total_start_time).total_seconds()
        chunk_elapsed = (datetime.now() - chunk_start_time).total_seconds()
        
        print(f"\n\n{'='*60}")
        print(f"Recording complete:")
        print(f"  Total Duration: {total_elapsed:.1f}s")
        print(f"  Total Frames: {frame_count}")
        print(f"  Average FPS: {total_elapsed/frame_count:.2f}")
        print(f"  Total Chunks: {chunk_number}")
        print(f"\nFinal chunk {chunk_number}:")
        print(f"  Duration: {chunk_elapsed:.1f}s")
        print(f"  Frames: {chunk_frame_count}")
        print(f"  File: {current_filepath}")
        print(f"{'='*60}")
        
        cap.release()
        out.release()
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(
        description='Raspberry Pi Webcam Recorder with auto-chunking',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Recording parameters w/ defaults
    parser.add_argument('-o', '--output', 
                       default='/mnt/video_storage',
                       help='Output directory for recordings')
    parser.add_argument('-r', '--resolution',
                       default='1920x1080',
                       help='Video resolution (WIDTHxHEIGHT)')
    parser.add_argument('-f', '--fps',
                       type=int,
                       default=30,
                       help='Frame rate')
    parser.add_argument('-c', '--codec',
                       default='H264',
                       choices=['H264', 'MJPG', 'XVID', 'MP4V'],
                       help='Video codec')
    parser.add_argument('--format',
                       default='mp4',
                       help='Output file format')
    parser.add_argument('--camera',
                       type=int,
                       default=0,
                       help='Camera device index')
    parser.add_argument('--chunk-duration',
                       type=int,
                       default=300,
                       help='Duration of each video chunk in seconds (default: 300 = 5 minutes)')
    
    # Recording control
    parser.add_argument('-d', '--duration',
                       type=int,
                       help='Total recording duration in seconds (will be split into chunks)')
    parser.add_argument('--headless',
                       action='store_true',
                       default=True,
                       help='Run without video preview (for remote/SSH use)')
    
    # Utility commands
    parser.add_argument('-t', '--test',
                       action='store_true',
                       help='Test camera settings without recording')
    parser.add_argument('-l', '--list',
                       action='store_true',
                       help='List available camera capabilities')
    
    args = parser.parse_args()
    
    # Parse resolution
    try:
        width, height = map(int, args.resolution.split('x'))
    except:
        print(f"Error: Invalid resolution format '{args.resolution}'. Use WIDTHxHEIGHT (e.g., 1920x1080)")
        return 1
    
    # Validate chunk duration
    if args.chunk_duration < 10:
        print("Error: Chunk duration must be at least 10 seconds")
        return 1
    
    # List capabilities
    if args.list:
        print("Run this command to see camera capabilities:")
        print("  v4l2-ctl --list-formats-ext")
        return 0
    
    # Test mode
    if args.test:
        print(f"Testing camera {args.camera} at {width}x{height} @ {args.fps}fps...")
        cap = setup_camera(width, height, args.fps, args.camera)
        
        if args.headless:
            print("Capturing test frame...")
            ret, frame = cap.read()
            if ret:
                print(f"[OK] Successfully captured {frame.shape[1]}x{frame.shape[0]} frame")
            else:
                print("[FAIL] Failed to capture frame")
        else:
            print("Showing preview. Press any key to close...")
            while True:
                ret, frame = cap.read()
                if ret:
                    cv2.imshow('Camera Test', frame)
                if cv2.waitKey(1) != -1:
                    break
            cv2.destroyAllWindows()
        
        cap.release()
        return 0
    
    # Record video
    print(f"Starting recording:")
    print(f"  Output: {args.output}")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {args.fps}")
    print(f"  Codec: {args.codec}")
    print(f"  Camera: {args.camera}")
    print(f"  Chunk Duration: {args.chunk_duration}s ({args.chunk_duration//60} minutes)")
    if args.duration:
        num_chunks = (args.duration + args.chunk_duration - 1) // args.chunk_duration
        print(f"  Total Duration: {args.duration}s (~{num_chunks} chunks)")
    else:
        print(f"  Total Duration: Unlimited (Ctrl+C to stop)")
    if args.headless:
        print(f"  Mode: Headless (no preview)")
    
    record_video(
        args.output,
        width,
        height,
        args.fps,
        args.codec,
        args.format,
        args.camera,
        args.duration,
        args.headless,
        args.chunk_duration
    )
    
    return 0

if __name__ == "__main__":
    exit(main())