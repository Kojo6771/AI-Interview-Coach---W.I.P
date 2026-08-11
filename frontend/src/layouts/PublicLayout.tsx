import { Outlet } from "react-router-dom";

export default function PublicLayout() {
  return (
    <>
      <header>AI Interview Coach</header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
