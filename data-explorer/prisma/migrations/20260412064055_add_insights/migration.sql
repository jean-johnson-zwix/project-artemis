-- CreateTable
CREATE TABLE "insights" (
    "insight_id" UUID NOT NULL,
    "detection_id" UUID NOT NULL,
    "what" TEXT NOT NULL,
    "why" TEXT NOT NULL,
    "evidence" JSONB NOT NULL,
    "confidence" TEXT NOT NULL,
    "remaining_life_years" DOUBLE PRECISION,
    "recommended_actions" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "insights_pkey" PRIMARY KEY ("insight_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "insights_detection_id_key" ON "insights"("detection_id");

-- CreateIndex
CREATE INDEX "insights_detection_id_idx" ON "insights"("detection_id");

-- AddForeignKey
ALTER TABLE "insights" ADD CONSTRAINT "insights_detection_id_fkey" FOREIGN KEY ("detection_id") REFERENCES "detections"("detection_id") ON DELETE RESTRICT ON UPDATE CASCADE;
