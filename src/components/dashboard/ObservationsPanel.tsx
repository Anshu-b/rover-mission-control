import { Eye } from "lucide-react";
import DashboardPanel from "./DashboardPanel";

interface Observation {
  id: string;
  type: string;
  description: string;
  confidence: number;
  timestamp: string;
}

const mockObservations: Observation[] = [
  {
    id: "OBS-047",
    type: "Mineral",
    description: "Subsurface ice detected at 12cm depth",
    confidence: 94,
    timestamp: "2m ago",
  },
  {
    id: "OBS-046",
    type: "Terrain",
    description: "Smooth basalt formation — possible lava flow",
    confidence: 87,
    timestamp: "8m ago",
  },
  {
    id: "OBS-045",
    type: "Atmosphere",
    description: "CO₂ spike near crater rim sector B",
    confidence: 72,
    timestamp: "15m ago",
  },
  {
    id: "OBS-044",
    type: "Biological",
    description: "Organic compound trace — inconclusive",
    confidence: 31,
    timestamp: "22m ago",
  },
  {
    id: "OBS-043",
    type: "Geology",
    description: "Sedimentary layering in exposed cliff face",
    confidence: 89,
    timestamp: "34m ago",
  },
];

const confidenceColor = (conf: number) => {
  if (conf >= 80) return "text-success";
  if (conf >= 60) return "text-accent";
  if (conf >= 40) return "text-warning";
  return "text-destructive";
};

const confidenceBg = (conf: number) => {
  if (conf >= 80) return "bg-success/10";
  if (conf >= 60) return "bg-accent/10";
  if (conf >= 40) return "bg-warning/10";
  return "bg-destructive/10";
};

const ObservationsPanel = () => {
  return (
    <DashboardPanel
      title="Latest Observations"
      icon={<Eye className="w-4 h-4" />}
      statusIndicator={
        <span className="font-mono text-[10px] text-muted-foreground">
          {mockObservations.length} RECENT
        </span>
      }
    >
      <div className="space-y-2">
        {mockObservations.map((obs, i) => (
          <div
            key={obs.id}
            className="flex items-start gap-3 p-2.5 rounded-md bg-secondary/20 border border-border hover:border-primary/30 transition-colors animate-data-stream"
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-mono text-[10px] text-primary">{obs.id}</span>
                <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                  {obs.type}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground ml-auto flex-shrink-0">
                  {obs.timestamp}
                </span>
              </div>
              <p className="font-mono text-xs text-foreground/80 truncate">
                {obs.description}
              </p>
            </div>
            <div className={`flex-shrink-0 px-2 py-1 rounded ${confidenceBg(obs.confidence)}`}>
              <span className={`font-mono text-xs font-bold ${confidenceColor(obs.confidence)}`}>
                {obs.confidence}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </DashboardPanel>
  );
};

export default ObservationsPanel;
