"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

export interface PublicConfig {
  playground_enabled: boolean;
  loaded: boolean;
}

const defaultConfig: PublicConfig = {
  playground_enabled: false,
  loaded: false,
};

export const PublicConfigContext = createContext<PublicConfig>(defaultConfig);

export function usePublicConfig() {
  return useContext(PublicConfigContext);
}

export function usePublicConfigLoader() {
  const [config, setConfig] = useState<PublicConfig>(defaultConfig);

  useEffect(() => {
    api
      .publicConfig()
      .then((data) => setConfig({ ...data, loaded: true }))
      .catch(() => setConfig({ ...defaultConfig, loaded: true }));
  }, []);

  return config;
}