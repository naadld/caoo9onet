@echo off
cd /d %~dp0
if "%~1"=="" (
    set /p video_path="Keo tha file video MP4 vao day va nhan Enter: "
) else (
    set video_path="%~1"
)
echo Dang tao JSON cho file: %video_path%
python transcribe_english.py %video_path%
pause
