import { useRef, useEffect, useCallback } from 'react'

const API_BASE = 'http://localhost:8000'

export function usePhotoCapture(sessionId) {
  const videoRef = useRef(null)         // pour l'affichage uniquement
  const streamRef = useRef(null)        // flux caméra
  const imageCaptureRef = useRef(null)  // API capture photo
  const timersRef = useRef([])

  // ─── Démarrer la caméra ────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream

      // Brancher sur la vidéo d'affichage
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {})
      }

      // Créer ImageCapture depuis le track vidéo
      // ImageCapture est l'API native pour capturer des photos
      const videoTrack = stream.getVideoTracks()[0]
      imageCaptureRef.current = new ImageCapture(videoTrack)

      console.log('✅ Caméra démarrée — ImageCapture prêt')
    } catch (err) {
      console.error('❌ Erreur caméra:', err)
    }
  }, [])

  // ─── Arrêter la caméra ────────────────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    imageCaptureRef.current = null
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current = []
    console.log('📷 Caméra arrêtée')
  }, [])

  // ─── Convertir un Blob en base64 ─────────────────────────────────────────
  const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  }

  // ─── Capturer une photo et l'envoyer ────────────────────────────────────
  const captureAndSend = useCallback(async (questionId, moment) => {
    if (!sessionId || !imageCaptureRef.current) return

    try {
      let imageBase64

      // Essayer ImageCapture d'abord (meilleure qualité)
      try {
        const blob = await imageCaptureRef.current.takePhoto({
          imageWidth: 640,
          imageHeight: 480,
        })
        imageBase64 = await blobToBase64(blob)
        console.log(`📷 Photo prise via ImageCapture (moment: ${moment})`)
      } catch (icErr) {
        // Fallback : grabFrame → canvas
        console.warn('ImageCapture.takePhoto échoué, fallback grabFrame')
        const imageBitmap = await imageCaptureRef.current.grabFrame()
        const canvas = document.createElement('canvas')
        canvas.width = imageBitmap.width
        canvas.height = imageBitmap.height
        const ctx = canvas.getContext('2d')
        ctx.drawImage(imageBitmap, 0, 0)
        imageBase64 = canvas.toDataURL('image/jpeg', 0.95)
        imageBitmap.close()
      }

      if (!imageBase64 || imageBase64.length < 5000) {
        console.warn(`⚠️ Image vide ignorée (moment: ${moment})`)
        return
      }

      const response = await fetch(`${API_BASE}/session/${sessionId}/photo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: questionId,
          moment: moment,
          image: imageBase64,
        }),
      })

      const data = await response.json()
      console.log(
        `📸 Photo — moment: ${moment} | ` +
        `émotion: ${data.dominant_emotion} | ` +
        `confiance: ${data.confidence_observed}`
      )

    } catch (err) {
      console.error(`❌ Capture échouée (${moment}):`, err.message)
    }
  }, [sessionId])

  // ─── Démarrer la capture pour une question ────────────────────────────────
  const startQuestion = useCallback((questionId, timeLimit = 30000) => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current = []

    const t1 = setTimeout(() => captureAndSend(questionId, 'start'), 2000)
    const t2 = setTimeout(() => captureAndSend(questionId, 'middle'), timeLimit / 2)
    const t3 = setTimeout(() => captureAndSend(questionId, 'end'), timeLimit * 0.8)

    timersRef.current = [t1, t2, t3]
  }, [captureAndSend])

  // ─── Capturer au moment de la validation ─────────────────────────────────
  const captureOnAnswer = useCallback((questionId) => {
    timersRef.current.forEach(t => clearTimeout(t))
    timersRef.current = []
    captureAndSend(questionId, 'end')
  }, [captureAndSend])

  // ─── Nettoyage ───────────────────────────────────────────────────────────
  useEffect(() => {
    return () => stopCamera()
  }, [stopCamera])

  return {
    videoRef,
    startCamera,
    stopCamera,
    startQuestion,
    captureOnAnswer,
  }
}