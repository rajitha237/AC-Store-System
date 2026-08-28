"use client";

import dynamic from "next/dynamic";

import type {
  TechnicianLocationAdminResponse,
} from "@/types/technician-location";

import styles from "./technician-live-map.module.css";


interface TechnicianLiveMapProps {
  locations:
    TechnicianLocationAdminResponse[];
}


const TechnicianLiveMapClient =
  dynamic(
    () =>
      import(
        "./technician-live-map-client"
      ),
    {
      ssr: false,
      loading: () => (
        <div
          className={
            styles.mapLoading
          }
        >
          Loading field map...
        </div>
      ),
    },
  );


export default function TechnicianLiveMap({
  locations,
}: TechnicianLiveMapProps) {
  return (
    <TechnicianLiveMapClient
      locations={locations}
    />
  );
}
