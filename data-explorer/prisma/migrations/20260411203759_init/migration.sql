-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "vector";

-- CreateEnum
CREATE TYPE "AssetStatus" AS ENUM ('OPERATING', 'MAINTENANCE', 'STANDBY');

-- CreateEnum
CREATE TYPE "Criticality" AS ENUM ('HIGH', 'MEDIUM', 'LOW');

-- CreateEnum
CREATE TYPE "SensorType" AS ENUM ('PRESSURE', 'TEMPERATURE', 'FLOW', 'LEVEL', 'VIBRATION', 'CURRENT', 'FREQUENCY', 'LOAD', 'CONCENTRATION');

-- CreateEnum
CREATE TYPE "QualityFlag" AS ENUM ('GOOD', 'BAD', 'INTERPOLATED', 'OFFLINE', 'UNCERTAIN');

-- CreateEnum
CREATE TYPE "Severity" AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "WorkOrderType" AS ENUM ('CORRECTIVE', 'PREVENTIVE', 'EMERGENCY', 'INSPECTION', 'MODIFICATION');

-- CreateEnum
CREATE TYPE "Priority" AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'EMERGENCY');

-- CreateEnum
CREATE TYPE "WorkOrderStatus" AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'DEFERRED');

-- CreateTable
CREATE TABLE "assets" (
    "asset_id" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "subtype" TEXT,
    "parent_id" TEXT,
    "area" TEXT,
    "location" TEXT,
    "manufacturer" TEXT,
    "model" TEXT,
    "install_date" TIMESTAMP(3),
    "status" "AssetStatus" NOT NULL,
    "criticality" "Criticality" NOT NULL,

    CONSTRAINT "assets_pkey" PRIMARY KEY ("asset_id")
);

-- CreateTable
CREATE TABLE "sensor_metadata" (
    "sensor_id" TEXT NOT NULL,
    "asset_id" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "sensor_type" "SensorType" NOT NULL,
    "unit" TEXT NOT NULL,
    "normal_min" DOUBLE PRECISION,
    "normal_max" DOUBLE PRECISION,
    "alarm_low" DOUBLE PRECISION,
    "alarm_high" DOUBLE PRECISION,
    "trip_low" DOUBLE PRECISION,
    "trip_high" DOUBLE PRECISION,
    "area" TEXT,
    "location" TEXT,

    CONSTRAINT "sensor_metadata_pkey" PRIMARY KEY ("sensor_id")
);

-- CreateTable
CREATE TABLE "timeseries" (
    "id" BIGSERIAL NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL,
    "sensor_id" TEXT NOT NULL,
    "asset_id" TEXT NOT NULL,
    "sensor_type" "SensorType" NOT NULL,
    "value" DOUBLE PRECISION NOT NULL,
    "unit" TEXT NOT NULL,
    "quality_flag" "QualityFlag" NOT NULL,

    CONSTRAINT "timeseries_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "failure_events" (
    "failure_event_id" TEXT NOT NULL,
    "scenario_id" TEXT,
    "asset_id" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "area" TEXT NOT NULL,
    "event_timestamp" TIMESTAMP(3) NOT NULL,
    "detected_by" TEXT,
    "severity" "Severity" NOT NULL,
    "safety_impact" TEXT,
    "failure_mode" TEXT NOT NULL,
    "root_cause" TEXT NOT NULL,
    "failure_mechanism" TEXT,
    "immediate_action" TEXT,
    "corrective_action" TEXT,
    "production_loss_bbl" DOUBLE PRECISION,
    "downtime_hours" DOUBLE PRECISION,

    CONSTRAINT "failure_events_pkey" PRIMARY KEY ("failure_event_id")
);

-- CreateTable
CREATE TABLE "work_orders" (
    "work_order_id" TEXT NOT NULL,
    "failure_event_id" TEXT,
    "asset_id" TEXT NOT NULL,
    "tag" TEXT NOT NULL,
    "area" TEXT NOT NULL,
    "work_order_type" "WorkOrderType" NOT NULL,
    "priority" "Priority" NOT NULL,
    "status" "WorkOrderStatus" NOT NULL,
    "raised_date" TIMESTAMP(3) NOT NULL,
    "scheduled_date" TIMESTAMP(3),
    "completed_date" TIMESTAMP(3),
    "reported_by" TEXT,
    "assigned_to" TEXT,
    "supervisor" TEXT,
    "work_description" TEXT NOT NULL,
    "findings" TEXT,
    "actions_taken" TEXT,
    "parts_replaced" TEXT,
    "labor_hours" DOUBLE PRECISION,
    "downtime_hours" DOUBLE PRECISION,
    "production_loss_bbl" DOUBLE PRECISION,
    "scenario_id" TEXT,

    CONSTRAINT "work_orders_pkey" PRIMARY KEY ("work_order_id")
);

-- CreateTable
CREATE TABLE "documents" (
    "doc_id" TEXT NOT NULL,
    "asset_id" TEXT,
    "doc_type" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "revision" TEXT,
    "author" TEXT,
    "approved_by" TEXT,
    "issue_date" TIMESTAMP(3),
    "content" TEXT NOT NULL,
    "embedding" vector(1536),

    CONSTRAINT "documents_pkey" PRIMARY KEY ("doc_id")
);

-- CreateIndex
CREATE INDEX "assets_parent_id_idx" ON "assets"("parent_id");

-- CreateIndex
CREATE INDEX "assets_area_idx" ON "assets"("area");

-- CreateIndex
CREATE INDEX "assets_status_idx" ON "assets"("status");

-- CreateIndex
CREATE INDEX "sensor_metadata_asset_id_idx" ON "sensor_metadata"("asset_id");

-- CreateIndex
CREATE INDEX "sensor_metadata_sensor_type_idx" ON "sensor_metadata"("sensor_type");

-- CreateIndex
CREATE INDEX "timeseries_sensor_id_timestamp_idx" ON "timeseries"("sensor_id", "timestamp");

-- CreateIndex
CREATE INDEX "timeseries_asset_id_timestamp_idx" ON "timeseries"("asset_id", "timestamp");

-- CreateIndex
CREATE INDEX "timeseries_timestamp_idx" ON "timeseries"("timestamp");

-- CreateIndex
CREATE INDEX "failure_events_asset_id_idx" ON "failure_events"("asset_id");

-- CreateIndex
CREATE INDEX "failure_events_event_timestamp_idx" ON "failure_events"("event_timestamp");

-- CreateIndex
CREATE INDEX "failure_events_severity_idx" ON "failure_events"("severity");

-- CreateIndex
CREATE INDEX "work_orders_asset_id_idx" ON "work_orders"("asset_id");

-- CreateIndex
CREATE INDEX "work_orders_status_idx" ON "work_orders"("status");

-- CreateIndex
CREATE INDEX "work_orders_raised_date_idx" ON "work_orders"("raised_date");

-- CreateIndex
CREATE INDEX "documents_asset_id_idx" ON "documents"("asset_id");

-- CreateIndex
CREATE INDEX "documents_doc_type_idx" ON "documents"("doc_type");

-- AddForeignKey
ALTER TABLE "assets" ADD CONSTRAINT "assets_parent_id_fkey" FOREIGN KEY ("parent_id") REFERENCES "assets"("asset_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "sensor_metadata" ADD CONSTRAINT "sensor_metadata_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("asset_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "timeseries" ADD CONSTRAINT "timeseries_sensor_id_fkey" FOREIGN KEY ("sensor_id") REFERENCES "sensor_metadata"("sensor_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "timeseries" ADD CONSTRAINT "timeseries_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("asset_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "failure_events" ADD CONSTRAINT "failure_events_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("asset_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "work_orders" ADD CONSTRAINT "work_orders_failure_event_id_fkey" FOREIGN KEY ("failure_event_id") REFERENCES "failure_events"("failure_event_id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "work_orders" ADD CONSTRAINT "work_orders_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("asset_id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("asset_id") ON DELETE SET NULL ON UPDATE CASCADE;
