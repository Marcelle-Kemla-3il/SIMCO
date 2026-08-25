import { useEffect, useRef } from 'react'

/**
 * DunningKrugerChart
 * 
 * Affiche la courbe de Dunning-Kruger avec le point de l'étudiant.
 * 
 * Props :
 *   dk  → objet dunning_kruger retourné par /quiz-results
 */
export default function DunningKrugerChart({ dk }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!dk || !canvasRef.current) return
    drawCurve(canvasRef.current, dk)
  }, [dk])

  if (!dk) return null

  const zoneColors = {
    red: '#e74c3c', orange: '#e67e22', yellow: '#f1c40f',
    teal: '#1abc9c', blue: '#3498db', green: '#2ecc71'
  }
  const zoneColor = zoneColors[dk.color] || '#4ecdc4'

  return (
    <div style={styles.wrapper}>
      {/* Titre */}
      <div style={styles.header}>
        <span style={styles.title}>📈 Courbe de Dunning-Kruger</span>
        <span style={{ ...styles.zoneBadge, background: zoneColor }}>
          {dk.zone_label}
        </span>
      </div>

      {/* Canvas */}
      <div style={styles.canvasWrapper}>
        <canvas
          ref={canvasRef}
          width={600}
          height={320}
          style={styles.canvas}
        />
      </div>

      {/* Légende */}
      <div style={styles.legend}>
        <LegendItem color="#3498db" label={`Point déclaré — ${dk.declared_confidence}%`} />
        <LegendItem color={zoneColor} label={`Position réelle — ${dk.actual_score}%`} />
        {dk.observed_confidence !== null && dk.observed_confidence !== undefined && (
          <LegendItem color="#2ecc71" label={`Confiance observée (visage) — ${dk.observed_confidence}%`} />
        )}
      </div>

      {/* Message */}
      <div style={{ ...styles.messageBox, borderColor: zoneColor }}>
        <p style={styles.message}>{dk.message}</p>
        <p style={styles.recommendation}>💡 {dk.recommendation}</p>
      </div>

      {/* Métriques */}
      <div style={styles.metricsRow}>
        <Metric label="Score réel"       value={`${dk.actual_score}%`}       color="#4ecdc4" />
        <Metric label="Confiance déclarée" value={`${dk.declared_confidence}%`} color="#3498db" />
        <Metric label="Indice DK"         value={dk.dk_index > 0 ? `+${dk.dk_index}` : `${dk.dk_index}`} color={zoneColor} />
        <Metric label="Calibration"       value={`${dk.calibration_score}%`}  color="#2ecc71" />
      </div>

      {/* Profil ML si disponible */}
      {dk.profil_ml && (
        <div style={styles.mlBox}>
          <span style={styles.mlLabel}>🤖 Profil ML</span>
          <span style={{ ...styles.mlBadge, background: zoneColor }}>
            {dk.profil_ml}
          </span>
          {dk.confidence_ml && (
            <span style={styles.mlConfidence}>
              Certitude : {Math.round(dk.confidence_ml * 100)}%
            </span>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Dessin de la courbe ──────────────────────────────────────────────────────

function drawCurve(canvas, dk) {
  const ctx = canvas.getContext('2d')
  const W = canvas.width
  const H = canvas.height
  const PAD = { top: 30, right: 30, bottom: 50, left: 50 }
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top  - PAD.bottom

  ctx.clearRect(0, 0, W, H)

  // ─── Fond ──────────────────────────────────────────────────────────────────
  ctx.fillStyle = '#0d1117'
  ctx.fillRect(0, 0, W, H)

  // ─── Grille ────────────────────────────────────────────────────────────────
  ctx.strokeStyle = '#21262d'
  ctx.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const x = PAD.left + (chartW / 4) * i
    const y = PAD.top  + (chartH / 4) * i
    ctx.beginPath(); ctx.moveTo(x, PAD.top);  ctx.lineTo(x, PAD.top + chartH);  ctx.stroke()
    ctx.beginPath(); ctx.moveTo(PAD.left, y); ctx.lineTo(PAD.left + chartW, y); ctx.stroke()
  }

  // ─── Axes ──────────────────────────────────────────────────────────────────
  ctx.strokeStyle = '#30363d'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(PAD.left, PAD.top)
  ctx.lineTo(PAD.left, PAD.top + chartH)
  ctx.lineTo(PAD.left + chartW, PAD.top + chartH)
  ctx.stroke()

  // Labels axes
  ctx.fillStyle = '#8b949e'
  ctx.font = '11px monospace'
  ctx.textAlign = 'center'
  ctx.fillText('Compétence réelle →', PAD.left + chartW / 2, H - 8)
  ctx.save()
  ctx.translate(14, PAD.top + chartH / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('Confiance perçue →', 0, 0)
  ctx.restore()

  // ─── Points DK sur la courbe ───────────────────────────────────────────────
  // La courbe DK classique en 5 points clés
  const curvePoints = [
    { x: 0,    y: 10  },   // départ bas
    { x: 15,   y: 90  },   // pic montagne stupide
    { x: 40,   y: 20  },   // vallée désespoir
    { x: 65,   y: 55  },   // pente illumination
    { x: 85,   y: 75  },   // plateau maîtrise
    { x: 100,  y: 80  },   // expert
  ]

  // Convertir en pixels
  const toPixel = (px, py) => ({
    x: PAD.left + (px / 100) * chartW,
    y: PAD.top  + chartH - (py / 100) * chartH
  })

  // Dessiner la courbe
  ctx.beginPath()
  ctx.strokeStyle = '#4ecdc4'
  ctx.lineWidth = 3
  ctx.shadowColor = '#4ecdc4'
  ctx.shadowBlur = 8

  const first = toPixel(curvePoints[0].x, curvePoints[0].y)
  ctx.moveTo(first.x, first.y)

  for (let i = 1; i < curvePoints.length; i++) {
    const prev = toPixel(curvePoints[i - 1].x, curvePoints[i - 1].y)
    const curr = toPixel(curvePoints[i].x,     curvePoints[i].y)
    const cpx  = (prev.x + curr.x) / 2
    ctx.bezierCurveTo(cpx, prev.y, cpx, curr.y, curr.x, curr.y)
  }
  ctx.stroke()
  ctx.shadowBlur = 0

  // ─── Labels zones ──────────────────────────────────────────────────────────
  const zoneLabels = [
    { x: 15, y: 96, label: 'Mont\nstupide' },
    { x: 40, y: 14, label: 'Vallée\ndésespoir' },
    { x: 75, y: 88, label: 'Plateau\nmaîtrise' },
  ]

  ctx.font = '9px monospace'
  ctx.fillStyle = '#555'
  ctx.textAlign = 'center'
  zoneLabels.forEach(z => {
    const p = toPixel(z.x, z.y)
    z.label.split('\n').forEach((line, i) => {
      ctx.fillText(line, p.x, p.y + i * 12)
    })
  })

  // ─── Point déclaré (bleu) ─────────────────────────────────────────────────
  const declaredX = dk.actual_score          // axe X = compétence réelle
  const declaredY = dk.declared_confidence   // axe Y = confiance déclarée
  const pDeclared = toPixel(declaredX, declaredY)

  ctx.beginPath()
  ctx.arc(pDeclared.x, pDeclared.y, 10, 0, Math.PI * 2)
  ctx.fillStyle = '#3498db'
  ctx.fill()
  ctx.strokeStyle = '#fff'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.fillStyle = '#fff'
  ctx.font = 'bold 10px monospace'
  ctx.textAlign = 'center'
  ctx.fillText('D', pDeclared.x, pDeclared.y + 4)

  // ─── Point observé ML (vert) si disponible ───────────────────────────────
  if (dk.observed_confidence !== null && dk.observed_confidence !== undefined) {
    const obsY = dk.observed_confidence
    const pObs = toPixel(declaredX, obsY)

    // Flèche entre déclaré et observé
    if (Math.abs(declaredY - obsY) > 5) {
      ctx.beginPath()
      ctx.strokeStyle = '#f39c12'
      ctx.lineWidth = 1.5
      ctx.setLineDash([4, 4])
      ctx.moveTo(pDeclared.x, pDeclared.y)
      ctx.lineTo(pObs.x, pObs.y)
      ctx.stroke()
      ctx.setLineDash([])
    }

    ctx.beginPath()
    ctx.arc(pObs.x, pObs.y, 10, 0, Math.PI * 2)
    ctx.fillStyle = '#2ecc71'
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()

    ctx.fillStyle = '#fff'
    ctx.font = 'bold 10px monospace'
    ctx.textAlign = 'center'
    ctx.fillText('O', pObs.x, pObs.y + 4)
  }

  // ─── Position réelle sur la courbe (teal) ────────────────────────────────
  // Trouver le Y sur la courbe pour ce X
  const curveY = interpolateCurve(curvePoints, declaredX)
  const pCurve = toPixel(declaredX, curveY)

  ctx.beginPath()
  ctx.arc(pCurve.x, pCurve.y, 8, 0, Math.PI * 2)
  ctx.fillStyle = '#e74c3c'
  ctx.fill()
  ctx.strokeStyle = '#fff'
  ctx.lineWidth = 2
  ctx.stroke()

  ctx.fillStyle = '#fff'
  ctx.font = 'bold 9px monospace'
  ctx.textAlign = 'center'
  ctx.fillText('R', pCurve.x, pCurve.y + 3)

  // ─── Légende interne ──────────────────────────────────────────────────────
  const legendItems = [
    { color: '#3498db', label: 'D = Déclaré' },
    { color: '#e74c3c', label: 'R = Réel' },
  ]
  if (dk.observed_confidence !== null && dk.observed_confidence !== undefined) {
    legendItems.push({ color: '#2ecc71', label: 'O = Observé (visage)' })
  }

  legendItems.forEach((item, i) => {
    const lx = PAD.left + 10
    const ly = PAD.top + 10 + i * 16
    ctx.beginPath()
    ctx.arc(lx, ly, 5, 0, Math.PI * 2)
    ctx.fillStyle = item.color
    ctx.fill()
    ctx.fillStyle = '#8b949e'
    ctx.font = '9px monospace'
    ctx.textAlign = 'left'
    ctx.fillText(item.label, lx + 10, ly + 4)
  })
}

// Interpolation linéaire sur la courbe
function interpolateCurve(points, x) {
  for (let i = 0; i < points.length - 1; i++) {
    if (x >= points[i].x && x <= points[i + 1].x) {
      const t = (x - points[i].x) / (points[i + 1].x - points[i].x)
      return points[i].y + t * (points[i + 1].y - points[i].y)
    }
  }
  return points[points.length - 1].y
}

// ─── Sous-composants ──────────────────────────────────────────────────────────

function LegendItem({ color, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 12, height: 12, borderRadius: '50%', background: color }} />
      <span style={{ fontSize: '0.8rem', color: '#8b949e' }}>{label}</span>
    </div>
  )
}

function Metric({ label, value, color }) {
  return (
    <div style={styles.metric}>
      <span style={{ ...styles.metricValue, color }}>{value}</span>
      <span style={styles.metricLabel}>{label}</span>
    </div>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = {
  wrapper: {
    background: '#161b22',
    border: '1px solid #21262d',
    borderRadius: 12,
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 8,
  },
  title: {
    fontSize: '1rem',
    fontWeight: 700,
    color: '#e6edf3',
  },
  zoneBadge: {
    padding: '4px 12px',
    borderRadius: 20,
    fontSize: '0.8rem',
    fontWeight: 700,
    color: '#0d1117',
  },
  canvasWrapper: {
    width: '100%',
    overflowX: 'auto',
    borderRadius: 8,
    border: '1px solid #21262d',
  },
  canvas: {
    display: 'block',
    maxWidth: '100%',
  },
  legend: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 16,
  },
  messageBox: {
    borderLeft: '3px solid',
    paddingLeft: 14,
  },
  message: {
    margin: '0 0 6px',
    fontSize: '0.95rem',
    color: '#e6edf3',
    lineHeight: 1.6,
  },
  recommendation: {
    margin: 0,
    fontSize: '0.85rem',
    color: '#8b949e',
    fontStyle: 'italic',
  },
  metricsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 10,
  },
  metric: {
    background: '#0d1117',
    borderRadius: 8,
    padding: '12px 8px',
    textAlign: 'center',
  },
  metricValue: {
    display: 'block',
    fontSize: '1.2rem',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  metricLabel: {
    display: 'block',
    fontSize: '0.7rem',
    color: '#555',
    marginTop: 4,
  },
  mlBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 14px',
    background: '#0d1117',
    borderRadius: 8,
    border: '1px solid #21262d',
  },
  mlLabel: {
    fontSize: '0.85rem',
    color: '#8b949e',
  },
  mlBadge: {
    padding: '3px 10px',
    borderRadius: 12,
    fontSize: '0.8rem',
    fontWeight: 700,
    color: '#0d1117',
  },
  mlConfidence: {
    fontSize: '0.8rem',
    color: '#555',
    marginLeft: 'auto',
  },
}