export function calculateHealthScore({
  sensors,
  latestValues,
  openWorkOrders,
  recentFailures,
}: {
  sensors: Array<{
    id: string
    normalMin: number | null
    normalMax: number | null
    alarmLow: number | null
    alarmHigh: number | null
  }>
  latestValues: Map<string, number>
  openWorkOrders: number
  recentFailures: number
}): number {
  let score = 100

  for (const sensor of sensors) {
    const value = latestValues.get(sensor.id)
    if (value === undefined) continue

    const normalMin = sensor.normalMin
    const normalMax = sensor.normalMax
    const alarmLow = sensor.alarmLow
    const alarmHigh = sensor.alarmHigh

    if (normalMin !== null && value < normalMin) score -= 5
    else if (normalMax !== null && value > normalMax) score -= 5

    if ((alarmLow !== null && value < alarmLow) || (alarmHigh !== null && value > alarmHigh)) {
      score -= 10
    }
  }

  if (openWorkOrders > 0) score -= 15
  if (recentFailures > 0) score -= 20

  return Math.max(0, Math.min(100, score))
}
