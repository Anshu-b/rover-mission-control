import { Mountain } from "lucide-react";
import DashboardPanel from "./DashboardPanel";

const terrainTypes = [
  { type: "Basalt Rock", percentage: 38, color: "bg-primary" },
  { type: "Regolith", percentage: 27, color: "bg-info" },
  { type: "Ice Deposits", percentage: 18, color: "bg-success" },
  { type: "Sandy Terrain", percentage: 12, color: "bg-accent" },
  { type: "Unknown", percentage: 5, color: "bg-destructive" },
];

const TerrainPanel = () => {
  return (
    <DashboardPanel
      title="Terrain Classification"
      icon={<Mountain className="w-4 h-4" />}
      statusIndicator={
        <span className="font-mono text-[10px] text-muted-foreground">
          5 TYPES DETECTED
        </span>
      }
    >
      <div className="space-y-3">
        {terrainTypes.map((terrain) => (
          <div key={terrain.type} className="space-y-1">
            <div className="flex justify-between items-baseline">
              <span className="font-mono text-xs text-foreground">{terrain.type}</span>
              <span className="font-mono text-xs text-muted-foreground">{terrain.percentage}%</span>
            </div>
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full ${terrain.color} rounded-full transition-all duration-1000`}
                style={{ width: `${terrain.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </DashboardPanel>
  );
};

export default TerrainPanel;
