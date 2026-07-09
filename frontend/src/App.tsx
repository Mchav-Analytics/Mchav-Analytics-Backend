import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
import { AuthCallbackPage } from "./features/auth/AuthCallbackPage";
import { LoginPage } from "./features/auth/LoginPage";
import { getAccessToken } from "./features/auth/authStorage";
import { DashboardPage } from "./features/dashboard/DashboardPage";
import { ProtectedRoute } from "./router/ProtectedRoute";

function PublicEntry() {
  return getAccessToken() ? <Navigate to="/dashboard" replace /> : <LoginPage />;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<PublicEntry />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
