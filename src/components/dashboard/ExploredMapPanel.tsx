import { Map } from "lucide-react";
import DashboardPanel from "./DashboardPanel";

const GRID_SIZE = 16;

const generateMapData = () => {
  const data: number[][] = [];
  for (let y = 0; y < GRID_SIZE; y++) {
    const row: number[] = [];
    for (let x = 0; x < GRID_SIZE; x++) {
      const dist = Math.sqrt((x - 8) ** 2 + (y - 10) ** 2);
      if (dist < 6) {
        row.push(Math.random() > 0.3 ? 2 : 1);
      } else if (dist < 9) {
        row.push(Math.random() > 0.5 ? 1 : 0);
      } else {
        row.push(0);
      }
    }
    data.push(row);
  }
  return data;
};

const mapData = generateMapData();

const cellColor = (val: number) => {
  if (val === 2) return "bg-primary/40 border-primary/30";
  if (val === 1) return "bg-primary/15 border-primary/10";
  return "bg-secondary/20 border-border/50";
};

const ExploredMapPanel = () => {
  const roverPos = { x: 8, y: 10 };

  return (
    <DashboardPanel
      title="Explored Map"
      icon={<Map className="w-4 h-4" />}
      statusIndicator={
        <span className="font-mono text-[10px] text-muted-foreground">
          COVERAGE: 34.2%
        </span>
      }
    >
      <div className="space-y-3">
        <div className="grid-bg rounded-md p-2 border border-border">
          <div
            className="grid gap-[1px] mx-auto"
            style={{
              gridTemplateColumns: `repeat(${GRID_SIZE}, 1fr)`,
              maxWidth: "100%",
              aspectRatio: "1",
            }}
          >
            {mapData.flatMap((row, y) =>
              row.map((cell, x) => (
                <div
                  key={`${x}-${y}`}
                  className={`rounded-[1px] border ${
                    x === roverPos.x && y === roverPos.y
                      ? "bg-accent border-accent animate-pulse-glow"
                      : cellColor(cell)
                  }`}
                />
              ))
            )}
          </div>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-mono text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-primary/40" /> Explored
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-primary/15" /> Partial
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-sm bg-accent" /> Rover
          </span>
        </div>
      </div>
    </DashboardPanel>
  );
};

export default ExploredMapPanel;
