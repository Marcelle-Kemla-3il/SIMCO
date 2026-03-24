import { useEffect, useRef, useState } from 'react';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

const WebcamAnalyzer = ({ onMetricsUpdate, isActive }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [faceLandmarker, setFaceLandmarker] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [faceDetected, setFaceDetected] = useState(false);
  const animationFrameRef = useRef(null);
  const metricsRef = useRef({
    blinkCount: 0,
    lastBlinkTime: 0,
    headMovements: 0,
    gazeOffScreen: 0,
    frameCount: 0,
    startTime: Date.now(),
    prevHeadPose: null,
    eyeClosedFrames: 0,
    // New: Timeline tracking (500ms intervals)
    timeline: [],
    lastSnapshotTime: Date.now(),
    // New: Facial expressions
    eyebrowRaiseCount: 0,
    mouthTensionSum: 0,
    eyeOpennessSum: 0,
    expressionChanges: 0,
    lastEyebrowHeight: 0
  });

  // Initialize MediaPipe Face Landmarker
  useEffect(() => {
    const initializeFaceLandmarker = async () => {
      try {
        const filesetResolver = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
        );
        
        const landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
          baseOptions: {
            modelAssetPath: `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`,
            delegate: "GPU"
          },
          outputFaceBlendshapes: true,
          runningMode: "VIDEO",
          numFaces: 1
        });
        
        setFaceLandmarker(landmarker);
        setIsInitialized(true);
      } catch (error) {
        console.error("Failed to initialize Face Landmarker:", error);
      }
    };

    initializeFaceLandmarker();

    return () => {
      if (faceLandmarker) {
        faceLandmarker.close();
      }
    };
  }, []);

  // Start/stop webcam
  useEffect(() => {
    if (!isActive || !isInitialized) return;

    const startWebcam = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 }
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
          processFrame();
        }
      } catch (error) {
        console.error("Failed to access webcam:", error);
      }
    };

    startWebcam();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = videoRef.current.srcObject.getTracks();
        tracks.forEach(track => track.stop());
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isActive, isInitialized]);

  // Calculate Eye Aspect Ratio (EAR)
  const calculateEAR = (eyeLandmarks) => {
    if (eyeLandmarks.length !== 6) return 0;
    
    const vertical1 = Math.hypot(
      eyeLandmarks[1].x - eyeLandmarks[5].x,
      eyeLandmarks[1].y - eyeLandmarks[5].y
    );
    const vertical2 = Math.hypot(
      eyeLandmarks[2].x - eyeLandmarks[4].x,
      eyeLandmarks[2].y - eyeLandmarks[4].y
    );
    const horizontal = Math.hypot(
      eyeLandmarks[0].x - eyeLandmarks[3].x,
      eyeLandmarks[0].y - eyeLandmarks[3].y
    );
    
    return (vertical1 + vertical2) / (2.0 * horizontal);
  };

  // Calculate eyebrow raise (surprise/confusion indicator)
  const calculateEyebrowRaise = (landmarks) => {
    // Using eyebrow landmarks: left=70, right=300
    // And eye landmarks: left=33, right=263
    try {
      const leftEyebrow = landmarks[70];
      const rightEyebrow = landmarks[300];
      const leftEye = landmarks[33];
      const rightEye = landmarks[263];
      
      const leftDistance = Math.abs(leftEyebrow.y - leftEye.y);
      const rightDistance = Math.abs(rightEyebrow.y - rightEye.y);
      
      return (leftDistance + rightDistance) / 2;
    } catch {
      return 0;
    }
  };

  // Calculate mouth tension (stress indicator)
  const calculateMouthTension = (landmarks) => {
    // Mouth corners: 61 (left), 291 (right)
    // Upper lip: 13, Lower lip: 14
    try {
      const leftCorner = landmarks[61];
      const rightCorner = landmarks[291];
      const upperLip = landmarks[13];
      const lowerLip = landmarks[14];
      
      const mouthWidth = Math.hypot(
        rightCorner.x - leftCorner.x,
        rightCorner.y - leftCorner.y
      );
      const mouthHeight = Math.hypot(
        upperLip.x - lowerLip.x,
        upperLip.y - lowerLip.y
      );
      
      // Tension = narrow mouth (low ratio)
      return mouthWidth > 0 ? mouthHeight / mouthWidth : 0;
    } catch {
      return 0;
    }
  };

  // Calculate head pose (yaw, pitch)
  const calculateHeadPose = (landmarks) => {
    // Simple approximation using key facial landmarks
    const nose = landmarks[1];
    const leftEye = landmarks[33];
    const rightEye = landmarks[263];
    const chin = landmarks[152];
    const forehead = landmarks[10];
    
    // Yaw (horizontal rotation)
    const eyeCenter = {
      x: (leftEye.x + rightEye.x) / 2,
      y: (leftEye.y + rightEye.y) / 2
    };
    const yaw = (nose.x - eyeCenter.x) * 100;
    
    // Pitch (vertical rotation)
    const faceCenter = {
      x: (chin.x + forehead.x) / 2,
      y: (chin.y + forehead.y) / 2
    };
    const pitch = (nose.y - faceCenter.y) * 100;
    
    return { yaw, pitch };
  };

  // Process video frames
  const processFrame = async () => {
    if (!faceLandmarker || !videoRef.current || !isActive) return;

    const video = videoRef.current;
    if (video.readyState !== video.HAVE_ENOUGH_DATA) {
      animationFrameRef.current = requestAnimationFrame(processFrame);
      return;
    }

    const startTimeMs = performance.now();
    const results = faceLandmarker.detectForVideo(video, startTimeMs);
    
    const metrics = metricsRef.current;
    metrics.frameCount++;

    if (results.faceLandmarks && results.faceLandmarks.length > 0) {
      setFaceDetected(true);
      const landmarks = results.faceLandmarks[0];
      
      // Blink detection using EAR
      const leftEyeLandmarks = [
        landmarks[33], landmarks[160], landmarks[158],
        landmarks[133], landmarks[153], landmarks[144]
      ];
      const rightEyeLandmarks = [
        landmarks[362], landmarks[385], landmarks[387],
        landmarks[263], landmarks[373], landmarks[380]
      ];
      
      const leftEAR = calculateEAR(leftEyeLandmarks);
      const rightEAR = calculateEAR(rightEyeLandmarks);
      const avgEAR = (leftEAR + rightEAR) / 2;
      
      // Detect blink (EAR < 0.21)
      if (avgEAR < 0.21) {
        metrics.eyeClosedFrames++;
      } else {
        if (metrics.eyeClosedFrames >= 2) {
          metrics.blinkCount++;
        }
        metrics.eyeClosedFrames = 0;
      }
      
      // Head pose tracking
      const currentPose = calculateHeadPose(landmarks);
      if (metrics.prevHeadPose) {
        const yawDiff = Math.abs(currentPose.yaw - metrics.prevHeadPose.yaw);
        const pitchDiff = Math.abs(currentPose.pitch - metrics.prevHeadPose.pitch);
        
        if (yawDiff > 5 || pitchDiff > 5) {
          metrics.headMovements++;
        }
      }
      metrics.prevHeadPose = currentPose;
      
      // Gaze detection (simplified - check if looking straight)
      const lookingStraight = Math.abs(currentPose.yaw) < 15 && Math.abs(currentPose.pitch) < 15;
      if (!lookingStraight) {
        metrics.gazeOffScreen++;
      }
      
      // Facial expressions
      const eyebrowHeight = calculateEyebrowRaise(landmarks);
      const mouthTension = calculateMouthTension(landmarks);
      
      metrics.eyeOpennessSum += avgEAR;
      metrics.mouthTensionSum += mouthTension;
      
      // Track eyebrow raises (expression changes)
      if (metrics.lastEyebrowHeight > 0) {
        const eyebrowChange = Math.abs(eyebrowHeight - metrics.lastEyebrowHeight);
        if (eyebrowChange > 0.02) {
          metrics.eyebrowRaiseCount++;
          metrics.expressionChanges++;
        }
      }
      metrics.lastEyebrowHeight = eyebrowHeight;
      
      // Timeline snapshot every 500ms
      const now = Date.now();
      if (now - metrics.lastSnapshotTime >= 500) {
        const elapsedSeconds = (now - metrics.startTime) / 1000;
        const currentBlinkRate = elapsedSeconds > 0 ? (metrics.blinkCount / elapsedSeconds) * 60 : 0;
        const currentGazeStability = metrics.frameCount > 0 ? 1 - (metrics.gazeOffScreen / metrics.frameCount) : 1;
        const currentStress = Math.min(
          (currentBlinkRate / 40) * 0.5 + 
          (metrics.headMovements / metrics.frameCount) * 0.3 +
          (1 - currentGazeStability) * 0.2,
          1
        );
        
        metrics.timeline.push({
          timestamp: parseFloat(elapsedSeconds.toFixed(1)),
          blink_rate: parseFloat(currentBlinkRate.toFixed(2)),
          gaze_stability: parseFloat(currentGazeStability.toFixed(3)),
          head_yaw: parseFloat(currentPose.yaw.toFixed(2)),
          head_pitch: parseFloat(currentPose.pitch.toFixed(2)),
          stress_estimate: parseFloat(currentStress.toFixed(3)),
          eyebrow_height: parseFloat(eyebrowHeight.toFixed(3)),
          mouth_tension: parseFloat(mouthTension.toFixed(3)),
          eye_openness: parseFloat(avgEAR.toFixed(3))
        });
        
        metrics.lastSnapshotTime = now;
      }
      
      // Draw landmarks on canvas
      if (canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'rgba(0, 255, 0, 0.5)';
        
        landmarks.forEach(landmark => {
          ctx.beginPath();
          ctx.arc(
            landmark.x * canvas.width,
            landmark.y * canvas.height,
            2, 0, 2 * Math.PI
          );
          ctx.fill();
        });
      }
    } else {
      setFaceDetected(false);
    }

    animationFrameRef.current = requestAnimationFrame(processFrame);
  };

  // Calculate and return current metrics
  const getCurrentMetrics = () => {
    const metrics = metricsRef.current;
    const elapsedSeconds = (Date.now() - metrics.startTime) / 1000;
    const blinkRate = elapsedSeconds > 0 ? (metrics.blinkCount / elapsedSeconds) * 60 : 0;
    const headMovementScore = metrics.headMovements / (metrics.frameCount || 1) * 100;
    const gazeStability = 1 - (metrics.gazeOffScreen / (metrics.frameCount || 1));
    const faceDetectionRate = metrics.frameCount > 0 ? 1 : 0;
    
    // Facial expression averages
    const avgEyeOpenness = metrics.frameCount > 0 ? metrics.eyeOpennessSum / metrics.frameCount : 0;
    const avgMouthTension = metrics.frameCount > 0 ? metrics.mouthTensionSum / metrics.frameCount : 0;
    
    return {
      // Aggregates (existing)
      blink_rate: parseFloat(blinkRate.toFixed(2)),
      head_movement_score: parseFloat(headMovementScore.toFixed(2)),
      gaze_stability: parseFloat(gazeStability.toFixed(4)),
      face_detection_rate: parseFloat(faceDetectionRate.toFixed(4)),
      total_blinks: metrics.blinkCount,
      total_head_movements: metrics.headMovements,
      frames_analyzed: metrics.frameCount,
      
      // New: Timeline data
      timeline: metrics.timeline,
      duration_seconds: parseFloat(elapsedSeconds.toFixed(1)),
      
      // New: Facial expressions
      facial_features: {
        eyebrow_raise_count: metrics.eyebrowRaiseCount,
        avg_mouth_tension: parseFloat(avgMouthTension.toFixed(3)),
        avg_eye_openness: parseFloat(avgEyeOpenness.toFixed(3)),
        expression_changes: metrics.expressionChanges
      }
    };
  };

  // Reset metrics for new question
  const resetMetrics = () => {
    metricsRef.current = {
      blinkCount: 0,
      lastBlinkTime: 0,
      headMovements: 0,
      gazeOffScreen: 0,
      frameCount: 0,
      startTime: Date.now(),
      prevHeadPose: null,
      eyeClosedFrames: 0,
      timeline: [],
      lastSnapshotTime: Date.now(),
      eyebrowRaiseCount: 0,
      mouthTensionSum: 0,
      eyeOpennessSum: 0,
      expressionChanges: 0,
      lastEyebrowHeight: 0
    };
  };

  // Expose methods to parent component
  useEffect(() => {
    if (onMetricsUpdate) {
      onMetricsUpdate({ getCurrentMetrics, resetMetrics });
    }
  }, [onMetricsUpdate]);

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-white rounded-lg shadow-lg p-2 border-2 border-gray-300">
        <div className="relative">
          <video
            ref={videoRef}
            className="w-48 h-36 rounded-lg object-cover"
            playsInline
            muted
          />
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 w-48 h-36 rounded-lg pointer-events-none"
          />
          <div className={`absolute top-2 left-2 px-2 py-1 rounded text-xs font-semibold ${
            faceDetected ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
          }`}>
            {faceDetected ? '✓ Face Detected' : '✗ No Face'}
          </div>
        </div>
        <p className="text-xs text-gray-600 text-center mt-1">
          {isInitialized ? 'Monitoring...' : 'Initializing...'}
        </p>
      </div>
    </div>
  );
};

export default WebcamAnalyzer;
