"use client";

import {
  Fragment,
  useEffect,
  useMemo,
} from "react";

import L from "leaflet";

import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import {
  ExternalLink,
  LocateFixed,
  MapPin,
  Navigation,
  UserRound,
  Wrench,
} from "lucide-react";

import type {
  CompletedServiceJobLocationResponse,
  TechnicianLocationAdminResponse,
} from "@/types/technician-location";

import "leaflet/dist/leaflet.css";

import styles from "./technician-live-map.module.css";


interface TechnicianLiveMapClientProps {
  locations:
    TechnicianLocationAdminResponse[];

  completedJobLocations:
    CompletedServiceJobLocationResponse[];
}


interface ValidMapLocation {
  location:
    TechnicianLocationAdminResponse;

  latitude: number;
  longitude: number;
}

interface ValidCompletedJobLocation {
  location:
    CompletedServiceJobLocationResponse;

  latitude: number;
  longitude: number;
}


function locationAge(
  seconds: number,
): string {
  if (seconds < 60) {
    return `${seconds}s ago`;
  }

  if (seconds < 3600) {
    return `${Math.floor(
      seconds / 60,
    )}m ago`;
  }

  if (seconds < 86400) {
    return `${Math.floor(
      seconds / 3600,
    )}h ago`;
  }

  return `${Math.floor(
    seconds / 86400,
  )}d ago`;
}


function statusLabel(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(
      /\b\w/g,
      (letter) =>
        letter.toUpperCase(),
    );
}


function googleMapsUrl(
  latitude: number,
  longitude: number,
): string {
  return (
    "https://www.google.com/maps/search/"
    + "?api=1&query="
    + encodeURIComponent(
      `${latitude},${longitude}`,
    )
  );
}


function FitTechnicianLocations({
  locations,
}: {
  locations: ValidMapLocation[];
}) {
  const map = useMap();

  useEffect(() => {
    if (locations.length === 0) {
      return;
    }

    if (locations.length === 1) {
      map.setView(
        [
          locations[0].latitude,
          locations[0].longitude,
        ],
        15,
      );

      return;
    }

    const bounds =
      L.latLngBounds(
        locations.map(
          (item) => [
            item.latitude,
            item.longitude,
          ],
        ),
      );

    map.fitBounds(
      bounds,
      {
        padding: [45, 45],
        maxZoom: 15,
      },
    );
  }, [
    locations,
    map,
  ]);

  return null;
}


export default function TechnicianLiveMapClient({
  locations,
  completedJobLocations,
}: TechnicianLiveMapClientProps) {
  const mapLocations =
    useMemo<ValidMapLocation[]>(
      () =>
        locations.flatMap(
          (location) => {
            const latitude =
              Number(
                location.latitude,
              );

            const longitude =
              Number(
                location.longitude,
              );

            if (
              !Number.isFinite(
                latitude,
              )
              || !Number.isFinite(
                longitude,
              )
              || latitude < -90
              || latitude > 90
              || longitude < -180
              || longitude > 180
            ) {
              return [];
            }

            return [
              {
                location,
                latitude,
                longitude,
              },
            ];
          },
        ),
      [locations],
    );

  const completedMapLocations =
    useMemo<ValidCompletedJobLocation[]>(
      () =>
        completedJobLocations.flatMap(
          (location) => {
            const latitude =
              Number(location.latitude);

            const longitude =
              Number(location.longitude);

            if (
              !Number.isFinite(latitude)
              || !Number.isFinite(longitude)
              || latitude < -90
              || latitude > 90
              || longitude < -180
              || longitude > 180
            ) {
              return [];
            }

            return [
              {
                location,
                latitude,
                longitude,
              },
            ];
          },
        ),
      [completedJobLocations],
    );

  const fitLocations =
    useMemo<ValidMapLocation[]>(
      () => [
        ...mapLocations,
        ...completedMapLocations.map(
          ({
            location,
            latitude,
            longitude,
          }) => ({
            location: {
              id: location.id,
              technician_id:
                location.technician_id,
              service_job_id:
                location.service_job_id,
              latitude,
              longitude,
              accuracy_meters:
                location.accuracy_meters,
              tracking_state: "stopped",
              recorded_at:
                location.recorded_at,
              technician_name:
                location.technician_name,
              service_job_number:
                location.service_job_number,
              presence_status: "offline" as const,
              age_seconds: 0,
            },
            latitude,
            longitude,
          }),
        ),
      ],
      [
        mapLocations,
        completedMapLocations,
      ],
    );


  if (
    fitLocations.length === 0
  ) {
    return (
      <div
        className={
          styles.emptyMap
        }
      >
        <div
          className={
            styles.emptyIcon
          }
        >
          <MapPin size={22} />
        </div>

        <div>
          <strong>
            Waiting for technician
            location
          </strong>

          <span>
            Start location sharing
            from the technician portal
            to display the field team
            on this map.
          </span>
        </div>
      </div>
    );
  }


  return (
    <div
      className={
        styles.mapShell
      }
    >
      <div
        className={
          styles.mapHeader
        }
      >
        <div>
          <div
            className={
              styles.mapEyebrow
            }
          >
            <LocateFixed size={15} />
            Field Map
          </div>

          <strong>
            Technician Map
          </strong>

          <span>
            {mapLocations.length}
            {" "}
            technician
            {mapLocations.length === 1
              ? ""
              : "s"}
            {" "}
            with coordinates
          </span>
        </div>

        <div
          className={
            styles.legend
          }
        >
          <span>
            <i
              className={
                styles.liveDot
              }
            />
            Live
          </span>

          <span>
            <i
              className={
                styles.staleDot
              }
            />
            Stale
          </span>

          <span>
            <i
              className={
                styles.offlineDot
              }
            />
            Offline
          </span>

          <span>
            <i
              className={
                styles.completedDot
              }
            />
            Completed Job
          </span>
        </div>
      </div>

      <div
        className={
          styles.mapFrame
        }
      >
        <MapContainer
          center={[
            fitLocations[0]
              .latitude,
            fitLocations[0]
              .longitude,
          ]}
          zoom={13}
          scrollWheelZoom
          className={
            styles.map
          }
        >
          <TileLayer
            attribution={
              "&copy; OpenStreetMap contributors"
            }
            url={
              "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }
          />

          <FitTechnicianLocations
            locations={
              fitLocations
            }
          />

          {mapLocations.map(
            ({
              location,
              latitude,
              longitude,
            }) => {
              const accuracy =
                Number(
                  location
                    .accuracy_meters,
                );

              const validAccuracy =
                Number.isFinite(
                  accuracy,
                )
                && accuracy > 0;

              const technicianColors = [
                "#2563eb",
                "#dc2626",
                "#16a34a",
                "#d97706",
                "#7c3aed",
                "#0891b2",
                "#db2777",
                "#4f46e5",
              ];

              const technicianColor =
                technicianColors[
                  Math.abs(
                    Number(
                      location
                        .technician_id,
                    ),
                  )
                  % technicianColors.length
                ];

              const color =
                technicianColor;

              return (
                <Fragment
                  key={
                    location
                      .technician_id
                  }
                >
                  {validAccuracy ? (
                    <Circle
                      center={[
                        latitude,
                        longitude,
                      ]}
                      radius={accuracy}
                      pathOptions={{
                        color,
                        fillColor:
                          color,
                        fillOpacity:
                          0.08,
                        weight: 1,
                      }}
                    />
                  ) : null}

                  <CircleMarker
                    center={[
                      latitude,
                      longitude,
                    ]}
                    radius={10}
                    pathOptions={{
                      color:
                        "#ffffff",
                      fillColor:
                        color,
                      fillOpacity: 1,
                      weight: 3,
                    }}
                  >
                    <Tooltip
                      direction="top"
                      offset={[0, -7]}
                    >
                      <strong>
                        {
                          location
                            .technician_name
                        }
                      </strong>

                      <br />

                      {statusLabel(
                        location
                          .presence_status,
                      )}
                    </Tooltip>

                    <Popup
                      minWidth={240}
                      maxWidth={300}
                    >
                      <div
                        className={
                          styles.popup
                        }
                      >
                        <div
                          className={
                            styles.popupHeader
                          }
                        >
                          <div
                            className={
                              styles.popupAvatar
                            }
                          >
                            <UserRound
                              size={18}
                            />
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
                              {
                                location
                                  .technician_id
                              }
                            </span>
                          </div>
                        </div>

                        <div
                          className={
                            `${styles.popupStatus} `
                            + `${
                              styles[
                                location
                                  .presence_status
                              ]
                            }`
                          }
                        >
                          {statusLabel(
                            location
                              .presence_status,
                          )}
                          {" · "}
                          {locationAge(
                            location
                              .age_seconds,
                          )}
                        </div>

                        <div
                          className={
                            styles.popupRow
                          }
                        >
                          <Wrench
                            size={15}
                          />

                          <span>
                            {
                              location
                                .service_job_number
                              ?? (
                                location
                                  .service_job_id
                                  ? (
                                      `Job #${
                                        location
                                          .service_job_id
                                      }`
                                    )
                                  : "No active job"
                              )
                            }
                          </span>
                        </div>

                        <div
                          className={
                            styles.popupRow
                          }
                        >
                          <Navigation
                            size={15}
                          />

                          <span>
                            {
                              latitude
                                .toFixed(6)
                            }
                            {", "}
                            {
                              longitude
                                .toFixed(6)
                            }
                          </span>
                        </div>

                        {validAccuracy ? (
                          <div
                            className={
                              styles.popupRow
                            }
                          >
                            <LocateFixed
                              size={15}
                            />

                            <span>
                              Accuracy ±
                              {
                                Math.round(
                                  accuracy,
                                )
                              }
                              m
                            </span>
                          </div>
                        ) : null}

                        <a
                          href={
                            googleMapsUrl(
                              latitude,
                              longitude,
                            )
                          }
                          target="_blank"
                          rel="noreferrer"
                          className={
                            styles.popupAction
                          }
                        >
                          <ExternalLink
                            size={15}
                          />
                          Open in Google Maps
                        </a>
                      </div>
                    </Popup>
                  </CircleMarker>
                </Fragment>
              );
            },
          )}

          {completedMapLocations.map(
            ({
              location,
              latitude,
              longitude,
            }) => {
              const accuracy =
                Number(
                  location.accuracy_meters,
                );

              const validAccuracy =
                Number.isFinite(accuracy)
                && accuracy > 0;

              const completedAt =
                new Date(
                  location.completed_at,
                );

              const completedAtLabel =
                Number.isNaN(
                  completedAt.getTime(),
                )
                  ? location.completed_at
                  : completedAt
                      .toLocaleString();

              return (
                <CircleMarker
                  key={
                    `completed-${location.id}`
                  }
                  center={[
                    latitude,
                    longitude,
                  ]}
                  radius={9}
                  pathOptions={{
                    color: "#ffffff",
                    fillColor: "#7c3aed",
                    fillOpacity: 1,
                    weight: 3,
                  }}
                >
                  <Tooltip
                    direction="top"
                    offset={[0, -7]}
                  >
                    <strong>
                      {
                        location
                          .service_job_number
                      }
                    </strong>

                    <br />

                    Completed Job
                  </Tooltip>

                  <Popup
                    minWidth={240}
                    maxWidth={310}
                  >
                    <div
                      className={
                        styles.popup
                      }
                    >
                      <div
                        className={
                          styles.popupHeader
                        }
                      >
                        <div
                          className={
                            styles
                              .completedPopupAvatar
                          }
                        >
                          <Wrench
                            size={18}
                          />
                        </div>

                        <div>
                          <strong>
                            {
                              location
                                .service_job_number
                            }
                          </strong>

                          <span>
                            Completed Job
                          </span>
                        </div>
                      </div>

                      <div
                        className={
                          styles.completedStatus
                        }
                      >
                        Completed
                      </div>

                      <div
                        className={
                          styles.popupRow
                        }
                      >
                        <UserRound
                          size={15}
                        />

                        <span>
                          {
                            location
                              .technician_name
                          }
                        </span>
                      </div>

                      <div
                        className={
                          styles.popupRow
                        }
                      >
                        <Wrench
                          size={15}
                        />

                        <span>
                          {
                            location
                              .service_job_number
                          }
                        </span>
                      </div>

                      <div
                        className={
                          styles.popupRow
                        }
                      >
                        <LocateFixed
                          size={15}
                        />

                        <span>
                          Completed:{" "}
                          {
                            completedAtLabel
                          }
                        </span>
                      </div>

                      <div
                        className={
                          styles.popupRow
                        }
                      >
                        <Navigation
                          size={15}
                        />

                        <span>
                          {
                            latitude
                              .toFixed(6)
                          }
                          {", "}
                          {
                            longitude
                              .toFixed(6)
                          }
                        </span>
                      </div>

                      {validAccuracy ? (
                        <div
                          className={
                            styles.popupRow
                          }
                        >
                          <LocateFixed
                            size={15}
                          />

                          <span>
                            Accuracy ±
                            {
                              Math.round(
                                accuracy,
                              )
                            }
                            m
                          </span>
                        </div>
                      ) : null}

                      <a
                        href={
                          googleMapsUrl(
                            latitude,
                            longitude,
                          )
                        }
                        target="_blank"
                        rel="noreferrer"
                        className={
                          styles.popupAction
                        }
                      >
                        <ExternalLink
                          size={15}
                        />
                        Open in Google Maps
                      </a>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            },
          )}

        </MapContainer>
      </div>
    </div>
  );
}
