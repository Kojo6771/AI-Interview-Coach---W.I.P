import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <>
      <header>AI Interview Coach</header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
