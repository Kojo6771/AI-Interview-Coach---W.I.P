import { createBrowserRouter } from "react-router-dom";
import PublicLayout from "../layouts/PublicLayout";
import AuthLayout from "../layouts/AuthLayout";
import AppLayout from "../layouts/AppLayout";

import LandingPage from "../pages/LandingPage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import DashboardPage from "../pages/DashboardPage";
import CVUploadPage from "../pages/CVUploadPage";
import InterviewSetupPage from "../pages/InterviewSetupPage";
import InterviewPage from "../pages/InterviewPage";
import ResultsPage from "../pages/ResultsPage";
import InterviewHistoryPage from "../pages/InterviewHistoryPage";
import ProgressPage from "../pages/ProgressPage";
import SettingsPage from "../pages/SettingsPage";

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      {
        path: "/",
        element: <LandingPage />,
      },
    ],
  },
  {
    element: <AuthLayout />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/register",
        element: <RegisterPage />,
      },
    ],
  },
  {
    element: <AppLayout />,
    children: [
      {
        path: "/dashboard",
        element: <DashboardPage />,
      },
      {
        path: "/cv/upload",
        element: <CVUploadPage />,
      },
      {
        path: "/interviews/new",
        element: <InterviewSetupPage />,
      },
      {
        path: "/interviews/:interviewId",
        element: <InterviewPage />,
      },
      {
        path: "/interviews/:interviewId/results",
        element: <ResultsPage />,
      },
      {
        path: "/interviews",
        element: <InterviewHistoryPage />,
      },
      {
        path: "/progress",
        element: <ProgressPage />,
      },
      {
        path: "/settings",
        element: <SettingsPage />,
      },
    ],
  },
]);
