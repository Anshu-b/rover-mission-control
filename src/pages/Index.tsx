import MissionHeader from "@/components/dashboard/MissionHeader";
import RoverStatePanel from "@/components/dashboard/RoverStatePanel";
import ExploredMapPanel from "@/components/dashboard/ExploredMapPanel";
import TerrainPanel from "@/components/dashboard/TerrainPanel";
import HabitabilityHeatmap from "@/components/dashboard/HabitabilityHeatmap";
import ObservationsPanel from "@/components/dashboard/ObservationsPanel";

const Index = () => {
  return (
    <div className="min-h-screen bg-background p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <MissionHeader />

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <RoverStatePanel />
          <ExploredMapPanel />
          <HabitabilityHeatmap />
          <TerrainPanel />
          <div className="md:col-span-2">
            <ObservationsPanel />
          </div>
        </div>

        <footer className="mt-6 text-center">
          <p className="font-mono text-[10px] text-muted-foreground tracking-widest">
            MISSION ELAPSED TIME: 47D 07H 23M · NEXT UPLINK WINDOW: 00:14:32
          </p>
        </footer>
      </div>
    </div>
  );
};

export default Index;
