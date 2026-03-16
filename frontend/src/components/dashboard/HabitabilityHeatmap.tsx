import { Thermometer } from "lucide-react";
import DashboardPanel from "./DashboardPanel";

const HEATMAP_SIZE = 12;

const generateHeatmapData = () => {
  const data: number[][] = [];
  for (let y = 0; y < HEATMAP_SIZE; y++) {
    const row: number[] = [];
    for (let x = 0; x < HEATMAP_SIZE; x++) {
      const hotspot1 = Math.exp(-((x - 3) ** 2 + (y - 4) ** 2) / 8);
      const hotspot2 = Math.exp(-((x - 9) ** 2 + (y - 8) ** 2) / 6);
      const val = Math.min(1, hotspot1 + hotspot2 + Math.random() * 0.15);
      row.push(val);
    }
    data.push(row);
  }
  return data;
};

const heatmapData = generateHeatmapData();

const heatColor = (val: number): string => {
  if (val > 0.7) return "bg-success";
  if (val > 0.5) return "bg-success/60";
  if (val > 0.3) return "bg-accent/50";
  if (val > 0.15) return "bg-destructive/30";
  return "bg-secondary/30";
};

const HabitabilityHeatmap = () => {
  return (
    <DashboardPanel
      title="Habitability Heatmap"
      icon={<Thermometer className="w-4 h-4" />}
      statusIndicator={
        <span className="font-mono text-[10px] text-success">
          2 ZONES VIABLE
        </span>
      }
    >
      <div className="space-y-3">
        <div className="rounded-md p-2 border border-border bg-secondary/10">
          <div
            className="grid gap-[2px] mx-auto"
            style={{
              gridTemplateColumns: `repeat(${HEATMAP_SIZE}, 1fr)`,
              maxWidth: "100%",
              aspectRatio: "1",
            }}
          >
            {heatmapData.flatMap((row, y) =>
              row.map((cell, x) => (
                <div
                  key={`${x}-${y}`}
                  className={`rounded-[2px] ${heatColor(cell)}`}
                  style={{ opacity: 0.4 + cell * 0.6 }}
                />
              ))
            )}
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
          <span>LOW</span>
          <div className="flex gap-1">
            <span className="w-3 h-2 rounded-sm bg-secondary/30" />
            <span className="w-3 h-2 rounded-sm bg-destructive/30" />
            <span className="w-3 h-2 rounded-sm bg-accent/50" />
            <span className="w-3 h-2 rounded-sm bg-success/60" />
            <span className="w-3 h-2 rounded-sm bg-success" />
          </div>
          <span>HIGH</span>
        </div>
      </div>
    </DashboardPanel>
  );
};

export default HabitabilityHeatmap;
