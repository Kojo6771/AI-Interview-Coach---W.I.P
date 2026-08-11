import { Outlet } from "react-router-dom";

export default function AppLayout() {
  return (
    <div>
      <aside>Navigation</aside>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
