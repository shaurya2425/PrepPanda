import { createBrowserRouter } from "react-router";
import { LandingPage } from "./components/pages/LandingPage";
import { LoginPage } from "./components/pages/LoginPage";
import { SignupPage } from "./components/pages/SignupPage";
import { DashboardPage } from "./components/pages/DashboardPage";
import { LibraryFlow } from "./components/pages/LibraryFlow";
import { StudyWorkspace } from "./components/pages/StudyWorkspace";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: LandingPage,
  },
  {
    path: "/login",
    Component: LoginPage,
  },
  {
    path: "/signup",
    Component: SignupPage,
  },
  {
    path: "/dashboard",
    Component: DashboardPage,
  },
  {
    path: "/library",
    Component: LibraryFlow,
  },
  {
    path: "/study/:chapterId",
    Component: StudyWorkspace,
  },
]);
