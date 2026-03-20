import React from "react";
import ReactDOM from "react-dom/client";
import { AppRouter } from "@/app/router";
import { AppProviders } from "@/app/providers";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <AppRouter />
    </AppProviders>
  </React.StrictMode>,
);
