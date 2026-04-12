import { PrismaClient } from '@prisma/client'
import { parse } from 'csv-parse'
import * as fs from 'fs'
import * as path from 'path'
import * as dotenv from 'dotenv'

dotenv.config()

const prisma = new PrismaClient()

const DATA_DIR = path.join(__dirname, '../../data')

function csvPath(filename: string) {
  return path.join(DATA_DIR, filename)
}

async function readCsv<T extends Record<string, string>>(filePath: string): Promise<T[]> {
  return new Promise((resolve, reject) => {
    const rows: T[] = []
    fs.createReadStream(filePath)
      .pipe(parse({ columns: true, skip_empty_lines: true, trim: true }))
      .on('data', (row: T) => rows.push(row))
      .on('end', () => resolve(rows))
      .on('error', reject)
  })
}

function nullable(val: string): string | null {
  return val === '' || val === 'null' || val === 'NULL' ? null : val
}

function nullableFloat(val: string): number | null {
  if (val === '' || val === 'null' || val === 'NULL') return null
  const n = parseFloat(val)
  return isNaN(n) ? null : n
}

function nullableDate(val: string): Date | null {
  if (val === '' || val === 'null' || val === 'NULL') return null
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

async function seedAssets() {
  console.log('Seeding assets...')
  const rows = await readCsv<Record<string, string>>(csvPath('assets.csv'))

  // Insert in two passes to handle self-referential FK
  // First pass: insert all without parent
  // Second pass: update parents
  const data = rows.map((r) => ({
    id: r.asset_id,
    tag: r.tag,
    name: r.name,
    type: r.type,
    subtype: nullable(r.subtype),
    parentId: null as string | null, // will set in pass 2
    area: nullable(r.area),
    location: nullable(r.location),
    manufacturer: nullable(r.manufacturer),
    model: nullable(r.model),
    installDate: nullableDate(r.install_date),
    status: r.status as 'OPERATING' | 'MAINTENANCE' | 'STANDBY',
    criticality: r.criticality as 'HIGH' | 'MEDIUM' | 'LOW',
  }))

  await prisma.asset.createMany({ data, skipDuplicates: true })

  // Now update parentIds
  for (const r of rows) {
    if (r.parent_id && r.parent_id !== '') {
      await prisma.asset.update({
        where: { id: r.asset_id },
        data: { parentId: r.parent_id },
      }).catch(() => {}) // ignore if parent doesn't exist
    }
  }

  console.log(`  Inserted ${data.length} assets`)
}

async function seedSensors() {
  console.log('Seeding sensor metadata...')
  const rows = await readCsv<Record<string, string>>(csvPath('sensor_metadata.csv'))

  const data = rows.map((r) => ({
    id: r.sensor_id,
    assetId: r.asset_id,
    tag: r.tag,
    name: r.name,
    sensorType: r.sensor_type as 'PRESSURE' | 'TEMPERATURE' | 'FLOW' | 'LEVEL' | 'VIBRATION' | 'CURRENT' | 'FREQUENCY' | 'LOAD' | 'CONCENTRATION',
    unit: r.unit,
    normalMin: nullableFloat(r.normal_min),
    normalMax: nullableFloat(r.normal_max),
    alarmLow: nullableFloat(r.alarm_low),
    alarmHigh: nullableFloat(r.alarm_high),
    tripLow: nullableFloat(r.trip_low),
    tripHigh: nullableFloat(r.trip_high),
    area: nullable(r.area),
    location: nullable(r.location),
  }))

  await prisma.sensorMetadata.createMany({ data, skipDuplicates: true })
  console.log(`  Inserted ${data.length} sensors`)
}

async function seedFailureEvents() {
  console.log('Seeding failure events...')
  const rows = await readCsv<Record<string, string>>(csvPath('failure_events.csv'))

  const data = rows.map((r) => ({
    id: r.failure_event_id,
    scenarioId: nullable(r.scenario_id),
    assetId: r.asset_id,
    tag: r.tag,
    area: r.area,
    eventTimestamp: new Date(r.event_timestamp),
    detectedBy: nullable(r.detected_by),
    severity: r.severity as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
    safetyImpact: nullable(r.safety_impact),
    failureMode: r.failure_mode,
    rootCause: r.root_cause,
    failureMechanism: nullable(r.failure_mechanism),
    immediateAction: nullable(r.immediate_action),
    correctiveAction: nullable(r.corrective_action),
    productionLossBbl: nullableFloat(r.production_loss_bbl),
    downtimeHours: nullableFloat(r.downtime_hours),
  }))

  let inserted = 0
  for (const row of data) {
    try {
      await prisma.failureEvent.create({ data: row })
      inserted++
    } catch {
      // skip invalid FK or duplicate
    }
  }
  console.log(`  Inserted ${inserted} failure events`)
}

async function seedDocuments() {
  console.log('Seeding documents...')
  const rows = await readCsv<Record<string, string>>(csvPath('documents.csv'))

  const data = rows.map((r) => ({
    id: r.doc_id,
    assetId: nullable(r.asset_id),
    docType: r.doc_type,
    title: r.title,
    revision: nullable(r.revision),
    author: nullable(r.author),
    approvedBy: nullable(r.approved_by),
    issueDate: nullableDate(r.issue_date),
    content: r.content,
  }))

  let inserted = 0
  for (const row of data) {
    try {
      await prisma.document.create({ data: row })
      inserted++
    } catch {
      // skip invalid FK or duplicate
    }
  }
  console.log(`  Inserted ${inserted} documents`)
}

async function seedWorkOrders() {
  console.log('Seeding work orders...')
  const rows = await readCsv<Record<string, string>>(csvPath('maintenance_history.csv'))

  const data = rows.map((r) => ({
    id: r.work_order_id,
    failureEventId: nullable(r.failure_event_id),
    assetId: r.asset_id,
    tag: r.tag,
    area: r.area,
    workOrderType: r.work_order_type as 'CORRECTIVE' | 'PREVENTIVE' | 'EMERGENCY' | 'INSPECTION' | 'MODIFICATION',
    priority: r.priority as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'EMERGENCY',
    status: r.status as 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED' | 'DEFERRED',
    raisedDate: new Date(r.raised_date),
    scheduledDate: nullableDate(r.scheduled_date),
    completedDate: nullableDate(r.completed_date),
    reportedBy: nullable(r.reported_by),
    assignedTo: nullable(r.assigned_to),
    supervisor: nullable(r.supervisor),
    workDescription: r.work_description,
    findings: nullable(r.findings),
    actionsTaken: nullable(r.actions_taken),
    partsReplaced: nullable(r.parts_replaced),
    laborHours: nullableFloat(r.labor_hours),
    downtimeHours: nullableFloat(r.downtime_hours),
    productionLossBbl: nullableFloat(r.production_loss_bbl),
    scenarioId: nullable(r.scenario_id),
  }))

  let inserted = 0
  for (const row of data) {
    try {
      await prisma.workOrder.create({ data: row })
      inserted++
    } catch {
      // skip invalid FK or duplicate
    }
  }
  console.log(`  Inserted ${inserted} work orders`)
}

async function seedTimeseries() {
  console.log('Seeding timeseries (this may take a while)...')
  const filePath = csvPath('timeseries.csv')

  const BATCH_SIZE = 5000
  type TRow = { timestamp: Date; sensorId: string; assetId: string; sensorType: 'PRESSURE' | 'TEMPERATURE' | 'FLOW' | 'LEVEL' | 'VIBRATION' | 'CURRENT' | 'FREQUENCY' | 'LOAD' | 'CONCENTRATION'; value: number; unit: string; qualityFlag: 'GOOD' | 'BAD' | 'INTERPOLATED' | 'OFFLINE' | 'UNCERTAIN' }
  let batch: TRow[] = []
  let total = 0

  await new Promise<void>((resolve, reject) => {
    const parser = fs.createReadStream(filePath).pipe(
      parse({ columns: true, skip_empty_lines: true, trim: true })
    )

    parser.on('data', async (row: Record<string, string>) => {
      batch.push({
        timestamp: new Date(row.timestamp),
        sensorId: row.sensor_id,
        assetId: row.asset_id,
        sensorType: row.sensor_type as 'PRESSURE' | 'TEMPERATURE' | 'FLOW' | 'LEVEL' | 'VIBRATION' | 'CURRENT' | 'FREQUENCY' | 'LOAD' | 'CONCENTRATION',
        value: parseFloat(row.value),
        unit: row.unit,
        qualityFlag: row.quality_flag as 'GOOD' | 'BAD' | 'INTERPOLATED' | 'OFFLINE' | 'UNCERTAIN',
      })

      if (batch.length >= BATCH_SIZE) {
        parser.pause()
        const currentBatch = batch
        batch = []
        try {
          await prisma.timeseries.createMany({
            data: currentBatch,
            skipDuplicates: true,
          })
          total += currentBatch.length
          if (total % 50000 === 0) console.log(`  ... ${total.toLocaleString()} rows inserted`)
        } catch (e) {
          console.error('Batch insert error:', e)
        }
        parser.resume()
      }
    })

    parser.on('end', async () => {
      if (batch.length > 0) {
        try {
          await prisma.timeseries.createMany({
            data: batch,
            skipDuplicates: true,
          })
          total += batch.length
        } catch (e) {
          console.error('Final batch error:', e)
        }
      }
      console.log(`  Total timeseries rows inserted: ${total.toLocaleString()}`)
      resolve()
    })

    parser.on('error', reject)
  })
}

async function main() {
  console.log('Starting seed...')

  await seedAssets()
  await seedSensors()
  await seedFailureEvents()
  await seedDocuments()
  await seedWorkOrders()
  await seedTimeseries()

  console.log('Seed complete!')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
