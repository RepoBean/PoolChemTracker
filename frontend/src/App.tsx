import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import LogTest from "./pages/LogTest";
import Dosing from "./pages/Dosing";
import Trends from "./pages/Trends";
import Consumption from "./pages/Consumption";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/log" element={<LogTest />} />
        <Route path="/dosing" element={<Dosing />} />
        <Route path="/trends" element={<Trends />} />
        <Route path="/consumption" element={<Consumption />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
