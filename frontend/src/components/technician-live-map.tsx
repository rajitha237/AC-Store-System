"use client";

import dynamic from "next/dynamic";

import type {
  CompletedServiceJobLocationResponse,
  TechnicianLocationAdminResponse,
} from "@/types/technician-location";

import styles from "./technician-live-map.module.css";


interface TechnicianLiveMapProps {
  locations:
    TechnicianLocationAdminResponse[];

  completedJobLocations:
    CompletedServiceJobLocationResponse[];
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
  completedJobLocations,
}: TechnicianLiveMapProps) {
  return (
    <TechnicianLiveMapClient
      locations={locations}
      completedJobLocations={
        completedJobLocations
      }
    />
  );
}
