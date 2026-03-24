import { useEffect, useRef } from 'react';

const CAPTURE_INTERVAL_MS = 10000;
const MAX_CAPTURED_FRAMES = 10;
const FOCUS_CHECK_INTERVAL_MS = 2000;

const WebcamAnalyzer = ({ onMetricsUpdate, isActive }) => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const captureLoopRef = useRef(null);
  const focusLoopRef = useRef(null);
  const faceDetectorRef = useRef(null);
  const metricsRef = useRef({
    startTime: Date.now(),
    capturedFrames: [],
    lastFrameCaptureTime: 0,
    nextCaptureAtMs: 0,
    framesAnalyzed: 0,
    focusStatus: 'focused',
    faceDetectionRate: 1,
    focusChecks: 0,
    checksWithFace: 0,
    consecutiveNoFaceChecks: 0,
    lastFocusCheckAt: null
  });

  const checkFocusFromFace = async () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return;

    metricsRef.current.focusChecks += 1;
    metricsRef.current.lastFocusCheckAt = Date.now();

    let hasFace = true;
    try {
      if (faceDetectorRef.current) {
        const faces = await faceDetectorRef.current.detect(video);
        hasFace = Array.isArray(faces) && faces.length > 0;
      } else {
        // Fallback: if video is live and tab is visible, assume focused.
        hasFace = !document.hidden;
      }
    } catch (error) {
      hasFace = !document.hidden;
    }

    if (hasFace) {
      metricsRef.current.checksWithFace += 1;
      metricsRef.current.consecutiveNoFaceChecks = 0;
      metricsRef.current.focusStatus = 'focused';
    } else {
      metricsRef.current.consecutiveNoFaceChecks += 1;
      metricsRef.current.focusStatus = metricsRef.current.consecutiveNoFaceChecks >= 2 ? 'not_focused' : 'uncertain';
    }

    metricsRef.current.faceDetectionRate =
      metricsRef.current.focusChecks > 0
        ? parseFloat((metricsRef.current.checksWithFace / metricsRef.current.focusChecks).toFixed(2))
        : 1;
  };

  const captureFrame = () => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return false;

    try {
      const frameCanvas = document.createElement('canvas');
      frameCanvas.width = video.videoWidth || 640;
      frameCanvas.height = video.videoHeight || 480;
      const frameCtx = frameCanvas.getContext('2d');
      frameCtx.drawImage(video, 0, 0, frameCanvas.width, frameCanvas.height);

      const elapsedMs = Date.now() - metricsRef.current.startTime;
      const frameDataUrl = frameCanvas.toDataURL('image/jpeg', 0.7);
      metricsRef.current.capturedFrames.push({
        index: metricsRef.current.capturedFrames.length + 1,
        timestamp_seconds: parseFloat((elapsedMs / 1000).toFixed(1)),
        image_data_url: frameDataUrl,
        image_base64: frameDataUrl.split(',')[1]
      });
      metricsRef.current.lastFrameCaptureTime = Date.now();
      return true;
    } catch (error) {
      console.error('Failed to capture frame:', error);
      return false;
    }
  };

  const startCaptureLoop = () => {
    if (captureLoopRef.current) clearInterval(captureLoopRef.current);

    captureLoopRef.current = setInterval(() => {
      const now = Date.now();
      const elapsedMs = now - metricsRef.current.startTime;
      metricsRef.current.framesAnalyzed += 1;

      // Capture first frame immediately (0s), then every 10s, up to 4 frames.
      if (
        metricsRef.current.capturedFrames.length < MAX_CAPTURED_FRAMES &&
        elapsedMs >= metricsRef.current.nextCaptureAtMs
      ) {
        const captured = captureFrame();
        if (captured) {
          metricsRef.current.nextCaptureAtMs += CAPTURE_INTERVAL_MS;
        }
      }
    }, 200);
  };

  const startFocusLoop = () => {
    if (focusLoopRef.current) clearInterval(focusLoopRef.current);
    focusLoopRef.current = setInterval(() => {
      checkFocusFromFace();
    }, FOCUS_CHECK_INTERVAL_MS);
  };

  useEffect(() => {
    if (!isActive) return;

    const startWebcam = async () => {
      try {
        if ('FaceDetector' in window) {
          faceDetectorRef.current = new window.FaceDetector({ maxDetectedFaces: 1, fastMode: true });
        } else {
          faceDetectorRef.current = null;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
          audio: false
        });

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          // First capture right when question is shown
          captureFrame();
          metricsRef.current.nextCaptureAtMs = CAPTURE_INTERVAL_MS;
          startCaptureLoop();
          startFocusLoop();
        }
      } catch (error) {
        console.error('Failed to access webcam:', error);
      }
    };

    startWebcam();

    return () => {
      if (captureLoopRef.current) {
        clearInterval(captureLoopRef.current);
        captureLoopRef.current = null;
      }
      if (focusLoopRef.current) {
        clearInterval(focusLoopRef.current);
        focusLoopRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [isActive]);

  const getCurrentMetrics = () => {
    const elapsedSeconds = (Date.now() - metricsRef.current.startTime) / 1000;

    // Keep old contract fields for backend compatibility
    return {
      blink_rate: 0,
      head_movement_score: 0,
      gaze_stability: metricsRef.current.focusStatus === 'focused' ? 1 : 0.4,
      face_detection_rate: metricsRef.current.faceDetectionRate,
      total_blinks: 0,
      total_head_movements: 0,
      frames_analyzed: metricsRef.current.framesAnalyzed,
      timeline: [],
      duration_seconds: parseFloat(elapsedSeconds.toFixed(1)),
      facial_features: {
        eyebrow_raise_count: 0,
        avg_mouth_tension: 0,
        avg_eye_openness: 0,
        expression_changes: 0
      },
      captured_frames: metricsRef.current.capturedFrames,
      // Backward compatibility
      captured_frames_after_20s: metricsRef.current.capturedFrames,
      captured_frames_count: metricsRef.current.capturedFrames.length,
      focus_status: metricsRef.current.focusStatus,
      consecutive_no_face_checks: metricsRef.current.consecutiveNoFaceChecks,
      focus_checks: metricsRef.current.focusChecks
    };
  };

  const resetMetrics = () => {
    metricsRef.current = {
      startTime: Date.now(),
      capturedFrames: [],
      lastFrameCaptureTime: 0,
      nextCaptureAtMs: 0,
      framesAnalyzed: 0,
      focusStatus: 'focused',
      faceDetectionRate: 1,
      focusChecks: 0,
      checksWithFace: 0,
      consecutiveNoFaceChecks: 0,
      lastFocusCheckAt: null
    };
    // Try immediate capture for the next question if webcam is already ready.
    setTimeout(() => {
      const captured = captureFrame();
      metricsRef.current.nextCaptureAtMs = captured ? CAPTURE_INTERVAL_MS : 0;
    }, 120);
  };

  useEffect(() => {
    if (onMetricsUpdate) {
      onMetricsUpdate({ getCurrentMetrics, resetMetrics });
    }
  }, [onMetricsUpdate]);

  // No visible webcam UI; hidden capture only
  return <video ref={videoRef} playsInline muted style={{ display: 'none' }} />;
};

export default WebcamAnalyzer;
