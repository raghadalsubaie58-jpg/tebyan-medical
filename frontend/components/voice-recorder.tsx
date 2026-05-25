"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Mic, MicOff, Loader2, Volume2 } from "lucide-react"

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000"

type RecorderState = "idle" | "recording" | "processing" | "error"

interface VoiceRecorderProps {
  /** Called with the transcribed text so the parent can send it to chat */
  onTranscription: (text: string) => void
  /** If true the component also plays back TTS of the last assistant reply */
  ttsText?: string
  disabled?: boolean
}

export function VoiceRecorder({ onTranscription, ttsText, disabled = false }: VoiceRecorderProps) {
  const [state, setState]       = useState<RecorderState>("idle")
  const [error, setError]       = useState<string | null>(null)
  const [playing, setPlaying]   = useState(false)
  const mediaRecorder           = useRef<MediaRecorder | null>(null)
  const chunks                  = useRef<Blob[]>([])
  const audioRef                = useRef<HTMLAudioElement | null>(null)
  const streamRef               = useRef<MediaStream | null>(null)

  // ── Cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
      audioRef.current?.pause()
    }
  }, [])

  // ── Start / stop recording ────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/ogg"

      const mr = new MediaRecorder(stream, { mimeType })
      mediaRecorder.current = mr
      chunks.current = []

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data) }
      mr.onstop = () => handleStop(mimeType)

      mr.start(250)   // collect in 250 ms chunks
      setState("recording")
    } catch {
      setError("لم يتم السماح بالوصول للميكروفون")
      setState("error")
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current?.state === "recording") {
      mediaRecorder.current.stop()
    }
    streamRef.current?.getTracks().forEach((t) => t.stop())
    setState("processing")
  }, [])

  const handleStop = useCallback(async (mimeType: string) => {
    const blob = new Blob(chunks.current, { type: mimeType })
    if (blob.size < 1000) {
      setError("الصوت قصير جداً — حاول مجدداً")
      setState("idle")
      return
    }

    const form = new FormData()
    form.append("audio", blob, `voice.${mimeType.split("/")[1].split(";")[0]}`)
    form.append("language", "ar")

    try {
      const res = await fetch(`${BACKEND}/api/voice/transcribe`, {
        method: "POST",
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      const { text } = await res.json()
      if (text?.trim()) {
        onTranscription(text.trim())
      } else {
        setError("لم يُتعرَّف على أي كلام — حاول مجدداً")
      }
    } catch {
      setError("فشل تحويل الصوت إلى نص")
    } finally {
      setState("idle")
    }
  }, [onTranscription])

  // ── TTS playback ──────────────────────────────────────────────────────────
  const playTTS = useCallback(async () => {
    if (!ttsText || playing) return
    setPlaying(true)
    try {
      const res = await fetch(`${BACKEND}/api/voice/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ttsText }),
      })
      if (!res.ok) throw new Error("TTS failed")
      const arrayBuf = await res.arrayBuffer()
      const blob     = new Blob([arrayBuf], { type: "audio/mpeg" })
      const url      = URL.createObjectURL(blob)
      const audio    = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setPlaying(false); URL.revokeObjectURL(url) }
      audio.onerror = () => { setPlaying(false); URL.revokeObjectURL(url) }
      await audio.play()
    } catch {
      setPlaying(false)
    }
  }, [ttsText, playing])

  const isRecording   = state === "recording"
  const isProcessing  = state === "processing"

  return (
    <div className="flex items-center gap-2">
      {/* Mic button */}
      <motion.button
        type="button"
        aria-label={isRecording ? "إيقاف التسجيل" : "بدء التسجيل الصوتي"}
        disabled={disabled || isProcessing}
        onClick={isRecording ? stopRecording : startRecording}
        whileTap={{ scale: 0.92 }}
        className={[
          "relative flex h-9 w-9 items-center justify-center rounded-full transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isRecording
            ? "bg-red-500 text-white hover:bg-red-600"
            : "bg-muted text-muted-foreground hover:bg-muted/80",
          (disabled || isProcessing) ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
        ].join(" ")}
      >
        <AnimatePresence mode="wait" initial={false}>
          {isProcessing ? (
            <motion.span key="spin" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Loader2 className="h-4 w-4 animate-spin" />
            </motion.span>
          ) : isRecording ? (
            <motion.span key="stop" initial={{ scale: 0.7, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.7, opacity: 0 }}>
              <MicOff className="h-4 w-4" />
            </motion.span>
          ) : (
            <motion.span key="mic" initial={{ scale: 0.7, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.7, opacity: 0 }}>
              <Mic className="h-4 w-4" />
            </motion.span>
          )}
        </AnimatePresence>

        {/* Recording pulse ring */}
        {isRecording && (
          <motion.span
            className="absolute inset-0 rounded-full border-2 border-red-400"
            animate={{ scale: [1, 1.4, 1], opacity: [0.8, 0, 0.8] }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}
      </motion.button>

      {/* TTS speaker button — only shown when ttsText is provided */}
      {ttsText && (
        <motion.button
          type="button"
          aria-label="استماع للرد"
          disabled={playing}
          onClick={playTTS}
          whileTap={{ scale: 0.92 }}
          className={[
            "flex h-9 w-9 items-center justify-center rounded-full transition-colors",
            "bg-muted text-muted-foreground hover:bg-muted/80",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            playing ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
          ].join(" ")}
        >
          <Volume2 className={`h-4 w-4 ${playing ? "animate-pulse text-blue-500" : ""}`} />
        </motion.button>
      )}

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.span
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            onAnimationComplete={() => setTimeout(() => setError(null), 3000)}
            className="text-xs text-destructive"
          >
            {error}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  )
}
