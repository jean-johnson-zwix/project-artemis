// Threshold breach detection
export type AnomalyType = 'ALARM_HIGH' | 'ALARM_LOW' | 'TRIP_HIGH' | 'TRIP_LOW'

export interface Anomaly {
  sensorId: string
  sensorName: string
  assetId: string
  assetName: string
  timestamp: Date
  value: number
  unit: string
  anomalyType: AnomalyType
  threshold: number
}
