import { Link } from "react-router-dom";
import { Button, Card } from "./ui";

export function NoPool() {
  return (
    <Card className="text-center space-y-3">
      <div className="text-4xl">🏊</div>
      <div className="font-medium">No pool yet</div>
      <p className="text-sm text-slate-500">
        Create your pool to start logging tests and getting TFP targets.
      </p>
      <Link to="/settings">
        <Button>Set up your pool</Button>
      </Link>
    </Card>
  );
}
