-- CreateTable
CREATE TABLE "detections" (
    "detection_id" UUID NOT NULL,
    "detected_at" TIMESTAMPTZ NOT NULL,
    "detection_type" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "asset_id" TEXT NOT NULL,
    "asset_tag" TEXT NOT NULL,
    "asset_name" TEXT NOT NULL,
    "area" TEXT NOT NULL,
    "detection_data" JSONB NOT NULL,

    CONSTRAINT "detections_pkey" PRIMARY KEY ("detection_id")
);

-- CreateIndex
CREATE INDEX "detections_asset_id_idx" ON "detections"("asset_id");

-- CreateIndex
CREATE INDEX "detections_detection_type_idx" ON "detections"("detection_type");

-- CreateIndex
CREATE INDEX "detections_detected_at_idx" ON "detections"("detected_at");
