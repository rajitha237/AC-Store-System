"use client";

import {
  AlertCircle,
  BriefcaseBusiness,
  ChevronRight,
  Clock3,
  LogOut,
  MapPin,
  PackagePlus,
  RefreshCw,
  Search,
  UserRound,
  Wrench,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import {
  getCurrentUser,
} from "@/lib/auth-api";
import {
  getServiceJobs,
} from "@/lib/service-jobs-api";
import {
  writeTechnicianLocation,
} from "@/lib/technician-location-api";

import type {
  ServiceJobDetailResponse,
} from "@/types/service-jobs";


import styles from "./page.module.css";


type TechnicianUser =
  Awaited<
    ReturnType<
      typeof getCurrentUser
    >
  >;





function normalizedRole(
  role: string | null | undefined,
): string {
  return (role ?? "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}


function isTechnicianRole(
  role: string | null | undefined,
): boolean {
  const value = normalizedRole(role);

  return (
    value === "technician"
    || value === "service_technician"
    || value.includes("technician")
  );
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


function formatDate(
  value: string | null | undefined,
): string {
  if (!value) {
    return "Not scheduled";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    "en-LK",
    {
      year: "numeric",
      month: "short",
      day: "2-digit",
    },
  ).format(parsed);
}


function jobCustomerName(
  job: ServiceJobDetailResponse,
): string {
  const candidate = job as unknown as {
    customer_name?: string | null;
  };

  return (
    candidate.customer_name
    ?? `Customer #${job.customer_id}`
  );
}


function jobItemName(
  job: ServiceJobDetailResponse,
): string {
  const candidate = job as unknown as {
    product_name?: string | null;
  };

  if (candidate.product_name) {
    return candidate.product_name;
  }

  const parts = [
    job.brand_name,
    job.model_number,
  ].filter(Boolean);

  return (
    parts.join(" ")
    || `Service Job ${job.job_number}`
  );
}


function jobLocation(
  job: ServiceJobDetailResponse,
): string {
  const candidate = job as unknown as {
    customer_address?: string | null;
    branch_name?: string | null;
  };

  return (
    candidate.customer_address
    ?? candidate.branch_name
    ?? "Service location"
  );
}


export default function TechnicianPage() {
  const router = useRouter();

  const [
    locationSharing,
    setLocationSharing,
  ] = useState(false);

  const [
    locationSending,
    setLocationSending,
  ] = useState(false);

  const [
    locationMessage,
    setLocationMessage,
  ] = useState("");

  const [
    locationError,
    setLocationError,
  ] = useState("");

  const [
    user,
    setUser,
  ] = useState<TechnicianUser | null>(
      null,
    );

  const [
    jobs,
    setJobs,
  ] = useState<ServiceJobDetailResponse[]>([]);

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

  const [
    search,
    setSearch,
  ] = useState("");


  const loadPortal = useCallback(
    async (
      background = false,
    ) => {
      if (background) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      try {
        const currentUser =
          await getCurrentUser();

        if (!isTechnicianRole(
          currentUser.role,
        )) {
          router.replace(
            "/dashboard",
          );

          return;
        }

        setUser(currentUser);

        const response =
          await getServiceJobs({
            page: 1,
            pageSize: 100,
            technicianId:
              currentUser.id,
          });

        const rawItems =
          (
            response as unknown as {
              items?: ServiceJobDetailResponse[];
            }
          ).items ?? [];

        const assignedJobs =
          rawItems.filter(
            (job) =>
              job.technician_id
              === currentUser.id,
          );

        setJobs(assignedJobs);
      } catch (requestError) {
        const status =
          (
            requestError as {
              response?: {
                status?: number;
              };
            }
          ).response?.status;

        if (
          status === 401
          || status === 403
        ) {
          router.replace(
            "/login",
          );

          return;
        }

        setError(
          "Unable to load technician jobs. Please try again.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [router],
  );


  useEffect(() => {
    const timer =
      window.setTimeout(
        () => {
          void loadPortal();
        },
        0,
      );

    return () => {
      window.clearTimeout(
        timer,
      );
    };
  }, [loadPortal]);



  const sendBrowserLocation =
    useCallback(
      async (
        position: GeolocationPosition,
      ) => {
        try {
          setLocationSending(true);
          setLocationError("");

          await writeTechnicianLocation({
            latitude:
              Number(
                position.coords.latitude
                  .toFixed(6),
              ),
            longitude:
              Number(
                position.coords.longitude
                  .toFixed(6),
              ),
            accuracy_meters:
              Number(
                position.coords.accuracy
                  .toFixed(2),
              ),
            client_recorded_at:
              new Date(
                position.timestamp,
              ).toISOString(),
            tracking_state: "active",
          });

          setLocationMessage(
            "Location updated successfully.",
          );
        } catch {
          setLocationError(
            "Unable to send your location.",
          );
        } finally {
          setLocationSending(false);
        }
      },
      [],
    );


  useEffect(() => {
    if (
      !user
      || user.role !== "technician"
    ) {
      return;
    }

    if (
      typeof navigator === "undefined"
      || !navigator.geolocation
    ) {
      const unsupportedTimer =
        window.setTimeout(() => {
          setLocationSharing(false);
          setLocationError(
            "Location tracking is required, but this device does not support browser location.",
          );
        }, 0);

      return () => {
        window.clearTimeout(
          unsupportedTimer,
        );
      };
    }

    let active = true;

    const watchId =
      navigator.geolocation.watchPosition(
        (position) => {
          if (!active) {
            return;
          }

          setLocationSharing(true);

          void sendBrowserLocation(
            position,
          );
        },
        (geoError) => {
          if (!active) {
            return;
          }

          setLocationSharing(false);

          if (
            geoError.code
            === geoError.PERMISSION_DENIED
          ) {
            setLocationError(
              "Location permission is required for technician access. Please enable location permission in your browser or device settings.",
            );
          } else if (
            geoError.code
            === geoError.POSITION_UNAVAILABLE
          ) {
            setLocationError(
              "Your current location is unavailable. Keep device location services enabled.",
            );
          } else if (
            geoError.code
            === geoError.TIMEOUT
          ) {
            setLocationError(
              "Location request timed out. Automatic tracking will continue trying while this portal is open.",
            );
          } else {
            setLocationError(
              "Unable to read your current location.",
            );
          }
        },
        {
          enableHighAccuracy: false,
          maximumAge: 60000,
          timeout: 60000,
        },
      );

    return () => {
      active = false;

      navigator.geolocation.clearWatch(
        watchId,
      );
    };
  }, [
    sendBrowserLocation,
    user,
  ]);


  const visibleJobs = useMemo(
    () => {
      const query =
        search.trim().toLowerCase();

      if (!query) {
        return jobs;
      }

      return jobs.filter(
        (job) => {
          const searchable = [
            job.job_number,
            jobCustomerName(job),
            jobItemName(job),
            job.serial_number,
            job.complaint,
            job.reported_issue,
            job.status,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return searchable.includes(
            query,
          );
        },
      );
    },
    [jobs, search],
  );


  const activeCount = useMemo(
    () =>
      jobs.filter(
        (job) =>
          job.status !== "ready"
          && job.status !== "delivered"
          && job.status !== "cancelled",
      ).length,
    [jobs],
  );


  const readyCount = useMemo(
    () =>
      jobs.filter(
        (job) =>
          job.status === "ready",
      ).length,
    [jobs],
  );


  function logout() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(
        "access_token",
      );

      window.localStorage.removeItem(
        "token",
      );
    }

    router.replace("/login");
  }


  if (loading) {
    return (
      <main
        className={
          styles.loadingPage
        }
      >
        <div
          className={
            styles.loadingCard
          }
        >
          <Wrench size={30} />

          <strong>
            Loading technician portal
          </strong>

          <span>
            Preparing your assigned jobs...
          </span>
        </div>
      </main>
    );
  }


  return (
    <main className={styles.page}>

      <section
        className={
          styles.locationCard
        }
      >
        <div
          className={
            styles.locationCardHeader
          }
        >
          <div>
            <strong>
              Technician Location
            </strong>

            <p>
              Share your live location while
              you are working on field jobs.
            </p>
          </div>

          <span
            className={
              locationSharing
                ? styles.locationLive
                : styles.locationOff
            }
          >
            {locationSharing
              ? "Live"
              : "Off"}
          </span>
        </div>

        <div
          className={
            styles.locationActions
          }
        >
          <div
          className={
            styles.locationStatus
          }
        >
          <MapPin size={17} />

          <div>
            <strong>
              Automatic Location Tracking
            </strong>

            <span>
              {locationSharing
                ? "Active while technician portal is open"
                : "Waiting for device location permission"}
            </span>
          </div>
        </div>
      </div>

        {locationSending ? (
          <p
            className={
              styles.locationMessage
            }
          >
            Updating location...
          </p>
        ) : null}

        {locationMessage ? (
          <p
            className={
              styles.locationMessage
            }
          >
            {locationMessage}
          </p>
        ) : null}

        {locationError ? (
          <p
            className={
              styles.locationError
            }
          >
            {locationError}
          </p>
        ) : null}
      </section>


      <header className={styles.header}>
        <div className={styles.brand}>
          <div
            className={
              styles.brandIcon
            }
          >
            <Wrench size={22} />
          </div>

          <div>
            <span
              className={
                styles.eyebrow
              }
            >
              Field Service
            </span>

            <h1>
              Technician Portal
            </h1>
          </div>
        </div>

        <button
          type="button"
          className={
            styles.logoutButton
          }
          onClick={logout}
          aria-label="Log out"
        >
          <LogOut size={19} />
          <span>Logout</span>
        </button>
      </header>

      <section
        className={
          styles.content
        }
      >
        <section
          className={
            styles.welcomeCard
          }
        >
          <div>
            <span
              className={
                styles.welcomeLabel
              }
            >
              Welcome back
            </span>

            <h2>
              {user?.full_name
                || user?.username
                || "Technician"}
            </h2>

            <p>
              View your assigned service
              jobs, add required parts,
              record the result and
              complete the job.
            </p>
          </div>

          <div
            className={
              styles.userBadge
            }
          >
            <UserRound size={20} />
            Technician
          </div>
        </section>

        <section
          className={
            styles.statsGrid
          }
        >
          <article
            className={
              styles.statCard
            }
          >
            <BriefcaseBusiness
              size={21}
            />

            <div>
              <strong>
                {jobs.length}
              </strong>
              <span>My Jobs</span>
            </div>
          </article>

          <article
            className={
              styles.statCard
            }
          >
            <Clock3 size={21} />

            <div>
              <strong>
                {activeCount}
              </strong>
              <span>Active</span>
            </div>
          </article>

          <article
            className={
              styles.statCard
            }
          >
            <PackagePlus size={21} />

            <div>
              <strong>
                {readyCount}
              </strong>
              <span>Completed</span>
            </div>
          </article>
        </section>

        <section
          className={
            styles.jobsSection
          }
        >
          <div
            className={
              styles.sectionHeader
            }
          >
            <div>
              <span
                className={
                  styles.eyebrow
                }
              >
                Assigned to me
              </span>

              <h2>My Jobs</h2>
            </div>

            <button
              type="button"
              className={
                styles.refreshButton
              }
              disabled={refreshing}
              onClick={() =>
                void loadPortal(true)
              }
            >
              <RefreshCw
                size={17}
                className={
                  refreshing
                    ? styles.spinning
                    : undefined
                }
              />

              Refresh
            </button>
          </div>

          <label
            className={
              styles.searchBox
            }
          >
            <Search size={18} />

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
              placeholder={
                "Search job, customer, item or serial"
              }
            />
          </label>

          {error ? (
            <div
              className={
                styles.errorBox
              }
            >
              <AlertCircle
                size={19}
              />

              <span>{error}</span>
            </div>
          ) : null}

          {!error
          && visibleJobs.length
            === 0 ? (
            <div
              className={
                styles.emptyState
              }
            >
              <BriefcaseBusiness
                size={34}
              />

              <h3>
                No jobs found
              </h3>

              <p>
                {search
                  ? "No assigned jobs match your search."
                  : "There are no service jobs assigned to you right now."}
              </p>
            </div>
          ) : null}

          <div
            className={
              styles.jobList
            }
          >
            {visibleJobs.map(
              (job) => (
                <button
                  key={job.id}
                  type="button"
                  className={
                    styles.jobCard
                  }
                  onClick={() =>
                    router.push(
                      `/technician/jobs/${job.id}`,
                    )
                  }
                >
                  <div
                    className={
                      styles.jobTop
                    }
                  >
                    <div>
                      <span
                        className={
                          styles.jobNumber
                        }
                      >
                        {job.job_number}
                      </span>

                      <h3>
                        {jobCustomerName(
                          job,
                        )}
                      </h3>
                    </div>

                    <span
                      className={
                        styles.statusBadge
                      }
                    >
                      {statusLabel(
                        job.status,
                      )}
                    </span>
                  </div>

                  <div
                    className={
                      styles.itemName
                    }
                  >
                    <Wrench size={17} />

                    <strong>
                      {jobItemName(job)}
                    </strong>
                  </div>

                  <p
                    className={
                      styles.complaint
                    }
                  >
                    {job.complaint
                      || job.reported_issue
                      || "No complaint details recorded."}
                  </p>

                  <div
                    className={
                      styles.jobMeta
                    }
                  >
                    <span>
                      <MapPin size={15} />
                      {jobLocation(job)}
                    </span>

                    <span>
                      <Clock3 size={15} />
                      {formatDate(
                        job.scheduled_visit_date
                        ?? job.expected_completion_date,
                      )}
                    </span>
                  </div>

                  <div
                    className={
                      styles.openJob
                    }
                  >
                    <span>
                      Open Job
                    </span>

                    <ChevronRight
                      size={19}
                    />
                  </div>
                </button>
              ),
            )}
          </div>
        </section>
      </section>
    </main>
  );
}
