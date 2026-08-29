"use client";

import {
  ExternalLink,
  LocateFixed,
  MapPin,
  RefreshCw,
  UserRound,
  Wrench,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getCompletedServiceJobLocations,
  getTechnicianLocations,
} from "@/lib/technician-location-api";

import TechnicianLiveMap from "@/components/technician-live-map";

import type {
  CompletedServiceJobLocationResponse,
  TechnicianLocationAdminResponse,
} from "@/types/technician-location";

import styles from "./technician-live-locations.module.css";


function locationAge(
  seconds: number,
): string {
  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  if (seconds < 3600) {
    return `${Math.floor(seconds / 60)}m ago`;
  }

  if (seconds < 86400) {
    return `${Math.floor(seconds / 3600)}h ago`;
  }

  return `${Math.floor(seconds / 86400)}d ago`;
}


function statusLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );
}


function coordinatesAvailable(
  location: TechnicianLocationAdminResponse,
): boolean {
  return (
    Number.isFinite(
      Number(location.latitude),
    )
    && Number.isFinite(
      Number(location.longitude),
    )
  );
}


function mapUrl(
  location: TechnicianLocationAdminResponse,
): string {
  return (
    "https://www.google.com/maps/search/"
    + "?api=1&query="
    + encodeURIComponent(
      `${location.latitude},${location.longitude}`,
    )
  );
}


export default function TechnicianLiveLocations() {
  const [
    locations,
    setLocations,
  ] = useState<
    TechnicianLocationAdminResponse[]
  >([]);

  const [
    completedJobLocations,
    setCompletedJobLocations,
  ] = useState<
    CompletedServiceJobLocationResponse[]
  >([]);

  const [
    loading,
    setLoading,
  ] = useState(true);

  const [
    refreshing,
    setRefreshing,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");


  const loadLocations =
    useCallback(
      async (
        manual = false,
      ) => {
        try {
          if (manual) {
            setRefreshing(true);
          }

          setError("");

          const [
            locationResponse,
            completedJobResponse,
          ] = await Promise.all([
            getTechnicianLocations(),
            getCompletedServiceJobLocations(),
          ]);

          setLocations(locationResponse);
          setCompletedJobLocations(
            completedJobResponse,
          );
        } catch (requestError) {
          const message =
            requestError instanceof Error
              ? requestError.message
              : (
                  "Unable to load "
                  + "technician locations."
                );

          setError(message);
        } finally {
          setLoading(false);
          setRefreshing(false);
        }
      },
      [],
    );


  useEffect(() => {
    const timeoutId =
      window.setTimeout(
        () => {
          void loadLocations();
        },
        0,
      );

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [loadLocations]);


  const summary = useMemo(
    () => {
      let live = 0;
      let stale = 0;
      let offline = 0;

      for (const location of locations) {
        if (
          location.presence_status
          === "live"
        ) {
          live += 1;
        } else if (
          location.presence_status
          === "stale"
        ) {
          stale += 1;
        } else {
          offline += 1;
        }
      }

      return {
        live,
        stale,
        offline,
      };
    },
    [locations],
  );


  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <div>
          <div className={styles.eyebrow}>
            <LocateFixed size={16} />
            Field Team
          </div>

          <h2>
            Live Technician Locations
          </h2>

          <p>
            Latest location shared by each
            active technician.
          </p>
        </div>

        <button
          type="button"
          className={styles.refreshButton}
          disabled={refreshing}
          onClick={() => {
            void loadLocations(true);
          }}
        >
          <RefreshCw
            size={17}
            className={
              refreshing
                ? styles.spinning
                : undefined
            }
          />

          {refreshing
            ? "Refreshing"
            : "Refresh"}
        </button>
      </div>

      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <span>Live</span>
          <strong>{summary.live}</strong>
        </div>

        <div className={styles.summaryCard}>
          <span>Stale</span>
          <strong>{summary.stale}</strong>
        </div>

        <div className={styles.summaryCard}>
          <span>Offline</span>
          <strong>{summary.offline}</strong>
        </div>

        <div className={styles.summaryCard}>
          <span>Total</span>
          <strong>{locations.length}</strong>
        </div>
      </div>

      <TechnicianLiveMap
        locations={locations}
        completedJobLocations={
          completedJobLocations
        }
      />

      {error ? (
        <div className={styles.error}>
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className={styles.empty}>
          Loading technician locations...
        </div>
      ) : locations.length === 0 ? (
        <div className={styles.empty}>
          No technician location has been
          shared yet.
        </div>
      ) : (
        <div className={styles.locationGrid}>
          {locations.map((location) => {
            const hasCoordinates =
              coordinatesAvailable(location);

            return (
              <article
                key={location.technician_id}
                className={styles.locationCard}
              >
                <div className={styles.cardTop}>
                  <div className={styles.person}>
                    <div
                      className={styles.avatar}
                    >
                      <UserRound size={19} />
                    </div>

                    <div>
                      <strong>
                        {
                          location
                            .technician_name
                        }
                      </strong>

                      <span>
                        Technician #
                        {location.technician_id}
                      </span>
                    </div>
                  </div>

                  <span
                    className={
                      `${styles.status} `
                      + `${
                        styles[
                          location
                            .presence_status
                        ]
                      }`
                    }
                  >
                    {statusLabel(
                      location.presence_status,
                    )}
                  </span>
                </div>

                <div className={styles.details}>
                  <div>
                    <Wrench size={16} />

                    <span>
                      {location
                        .service_job_number
                        ?? (
                          location.service_job_id
                            ? (
                                "Job #"
                                + location
                                  .service_job_id
                              )
                            : "No active job"
                        )}
                    </span>
                  </div>

                  <div>
                    <MapPin size={16} />

                    <span>
                      {hasCoordinates
                        ? (
                            `${location.latitude}, `
                            + `${location.longitude}`
                          )
                        : "Location unavailable"}
                    </span>
                  </div>
                </div>

                <div className={styles.meta}>
                  <span>
                    Updated{" "}
                    {locationAge(
                      location.age_seconds,
                    )}
                  </span>

                  <span>
                    Accuracy{" "}
                    {location.accuracy_meters
                      != null
                      ? (
                          `${Math.round(
                            Number(
                              location
                                .accuracy_meters,
                            ),
                          )} m`
                        )
                      : "—"}
                  </span>
                </div>

                {hasCoordinates ? (
                  <a
                    className={styles.mapButton}
                    href={mapUrl(location)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <MapPin size={16} />
                    Open Map
                    <ExternalLink size={14} />
                  </a>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
