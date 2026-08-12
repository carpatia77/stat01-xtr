import cv2
import os
import sys

def extract_frames(video_path, out_dir):
    if not os.path.exists(video_path):
        print(f"Video {video_path} not found.")
        return
        
    os.makedirs(out_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Error reading fps")
        return
        
    print(f"Processing {video_path} at {fps} fps")
    
    # 1 frame per minute
    frame_interval = int(fps * 60)
    
    count = 0
    minute = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % frame_interval == 0:
            out_file = os.path.join(out_dir, f"frame_{minute}m00s.jpg")
            cv2.imwrite(out_file, frame)
            minute += 1
            
        count += 1
        
    cap.release()
    print(f"Extracted {minute} frames to {out_dir}")

if __name__ == "__main__":
    extract_frames("pregao_01_07_2026.mp4", "frames_01_07")
    extract_frames("pregao_02_07_2026.mp4", "frames_02_07")
