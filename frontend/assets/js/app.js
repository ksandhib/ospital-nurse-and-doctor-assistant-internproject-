const current = session();
if (!current.token) location.href = "index.html";

const roleLabel = document.getElementById("roleLabel");
const welcome = document.getElementById("welcome");
let selectedPatientId = null;
let selectedPatientLabel = "";
roleLabel.textContent = `${current.role || "Clinic"} workspace`;
welcome.textContent = `Welcome, ${current.name || "clinician"}`;
document.body.dataset.role = current.role;

document.querySelectorAll(".doctor-only").forEach((el) => {
  if (current.role !== "doctor") el.style.display = "none";
});
document.querySelectorAll(".nurse-only").forEach((el) => {
  if (current.role !== "nurse") el.style.display = "none";
});

document.querySelectorAll(".nav-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    button.classList.add("active");
    document.getElementById(button.dataset.view).classList.add("active");
    if (button.dataset.view === "assistant") loadAssistantConversations();
  });
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  localStorage.clear();
  sessionStorage.clear();
  location.href = "index.html";
});

function formJson(form) {
  const data = Object.fromEntries(new FormData(form).entries());
  Object.keys(data).forEach((key) => {
    if (data[key] === "") data[key] = null;
    if (["age", "height_cm", "weight_kg", "patient_id", "doctor_id"].includes(key) && data[key] !== null) data[key] = Number(data[key]);
  });
  return data;
}

function table(rows, columns) {
  if (!rows.length) return "<p class='empty'>No records found.</p>";
  return `<table><thead><tr>${columns.map((col) => `<th>${col.label}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((col) => `<td>${col.render ? col.render(row) : row[col.key] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusBadge(status) {
  const label = {
    waiting: "Waiting",
    in_progress: "In Progress",
    completed: "Completed",
    cancelled: "Cancelled",
    scheduled: "Waiting",
    missed: "Cancelled"
  }[status] || status;
  return `<span class="status-badge status-${status}">${escapeHtml(label)}</span>`;
}

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString() : "-";
}

function formatTime(value) {
  if (!value) return "-";
  const [hour, minute] = value.split(":");
  return new Date(2000, 0, 1, Number(hour), Number(minute)).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "-";
}

function setCounter(element, value) {
  if (!element) return;
  const next = Number(value || 0);
  const previous = Number(element.dataset.value || element.textContent || 0);
  element.dataset.value = next;
  if (previous === next) {
    element.textContent = next.toLocaleString();
    return;
  }
  const started = performance.now();
  const duration = 450;
  const tick = (now) => {
    const progress = Math.min((now - started) / duration, 1);
    const currentValue = Math.round(previous + (next - previous) * progress);
    element.textContent = currentValue.toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

const dashboardCharts = {};
const chartColors = ["#2563EB", "#17a99b", "#69c7f4", "#b7791f", "#c2413d", "#64748b", "#11734d", "#b45309"];

function upsertChart(id, type, rows, options = {}) {
  const canvas = document.getElementById(id);
  if (!canvas || typeof Chart === "undefined") return;
  const labels = rows.map((item) => item.label);
  const values = rows.map((item) => item.value);
  const dataset = {
    label: options.label || "",
    data: values,
    borderColor: options.borderColor || "#2563EB",
    backgroundColor: options.backgroundColor || chartColors,
    fill: Boolean(options.fill),
    tension: 0.35
  };
  if (dashboardCharts[id]) dashboardCharts[id].destroy();
  dashboardCharts[id] = new Chart(canvas, {
    type,
    data: { labels, datasets: [dataset] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: options.indexAxis || "x",
      plugins: { legend: { display: ["pie", "doughnut"].includes(type) } },
      scales: ["pie", "doughnut"].includes(type) ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}

function setSelectedPatient(id, label) {
  selectedPatientId = Number(id);
  selectedPatientLabel = label || `Patient #${id}`;
  const context = document.getElementById("selectedPatientContext");
  if (context) context.textContent = `Selected patient: ${selectedPatientLabel}`;
}

async function loadPatientTimeline(id, label) {
  setSelectedPatient(id, label);
  const data = await api(`/patients/${id}/timeline`);
  timeline.innerHTML = [
    ...data.visits.map((v) => `<article><strong>Visit</strong><span>${new Date(v.at).toLocaleString()}</span><p>${escapeHtml(v.symptoms)}</p><p>${escapeHtml(v.diagnosis || "Diagnosis pending")}</p></article>`),
    ...data.vitals.map((v) => `<article><strong>Vitals</strong><span>${new Date(v.at).toLocaleString()}</span><p>BP ${v.data.systolic_bp || "-"} / ${v.data.diastolic_bp || "-"}, Pulse ${v.data.pulse || "-"}</p></article>`),
    ...data.documents.map((d) => `<article><strong>${escapeHtml(d.type)}</strong><span>${new Date(d.at).toLocaleString()}</span><p>${escapeHtml(d.title)}</p></article>`)
  ].join("") || "<p class='empty'>No timeline events yet.</p>";
}

async function loadDashboard() {
  try {
    const dashboard = await api("/dashboard/live");
    const stats = dashboard.stats;
    if (current.role === "doctor") {
      cardOneLabel.textContent = "Total Patients";
      cardTwoLabel.textContent = "Today's Appointments";
      cardThreeLabel.textContent = "Waiting Appointments";
      cardFourLabel.textContent = "Completed Today";
      cardFiveLabel.textContent = "Total Medicines";
      cardSixLabel.textContent = "Today's Consultations";
      cardSevenLabel.textContent = "Pending Follow-ups";
      cardEightLabel.textContent = "AI Recommendations Today";
      setCounter(statPatients, stats.total_patients);
      setCounter(statAppointments, stats.todays_appointments);
      setCounter(statFollowups, stats.waiting_appointments);
      setCounter(statStock, stats.completed_appointments_today);
      setCounter(statFive, stats.total_medicines);
      setCounter(statSix, stats.todays_consultations);
      setCounter(statSeven, stats.pending_followups);
      setCounter(statEight, stats.ai_recommendations_today);
    } else {
      cardOneLabel.textContent = "Total Registered Patients";
      cardTwoLabel.textContent = "Today's New Patients";
      cardThreeLabel.textContent = "Today's Appointments";
      cardFourLabel.textContent = "Waiting Patients";
      cardFiveLabel.textContent = "Completed Appointments";
      cardSixLabel.textContent = "Uploaded Lab Reports";
      cardSevenLabel.textContent = "Follow-up Patients";
      cardEightLabel.textContent = "Pending Registrations";
      setCounter(statPatients, stats.total_patients);
      setCounter(statAppointments, stats.todays_new_patients);
      setCounter(statFollowups, stats.todays_appointments);
      setCounter(statStock, stats.waiting_appointments);
      setCounter(statFive, stats.completed_appointments_today);
      setCounter(statSix, stats.uploaded_lab_reports);
      setCounter(statSeven, stats.follow_up_patients);
      setCounter(statEight, stats.pending_registrations);
    }
    if (apptToday) apptToday.textContent = stats.todays_appointments;
    if (apptWaiting) apptWaiting.textContent = stats.waiting_appointments;
    if (apptProgress) apptProgress.textContent = stats.todays_consultations;
    if (apptCompleted) apptCompleted.textContent = stats.completed_appointments_today;
    if (apptCancelled) apptCancelled.textContent = "0";

    todaySummary.innerHTML = [
      ["New Patients", dashboard.summary.new_patients],
      ["Appointments Booked", dashboard.summary.appointments_booked],
      ["Consultations Completed", dashboard.summary.consultations_completed],
      ["Prescriptions Generated", dashboard.summary.prescriptions_generated],
      ["Medicines Added", dashboard.summary.medicines_added]
    ].map(([label, value]) => `<article><span>${escapeHtml(label)}</span><strong>${Number(value || 0).toLocaleString()}</strong></article>`).join("");

    recentActivity.innerHTML = dashboard.activity.map((item) => `
      <article>
        <span>${formatDateTime(item.time)}</span>
        <strong>${escapeHtml(item.action)}</strong>
        <p>${escapeHtml(item.user || "Clinic staff")} - ${escapeHtml(item.patient || "-")}</p>
      </article>
    `).join("") || "<p class='empty'>No recent activity yet.</p>";

    recentPatients.innerHTML = table(dashboard.tables.recent_patients, [
      { label: "Patient ID", key: "patient_code" },
      { label: "Name", render: (row) => `<button class="mini-btn" data-patient="${row.id}" data-patient-label="${escapeHtml(`${row.patient_code} - ${row.name}`)}">${escapeHtml(row.name)}</button>` },
      { label: "Age", key: "age" },
      { label: "Gender", key: "gender" },
      { label: "Registration Date", render: (row) => formatDateTime(row.registration_date) }
    ]);
    dashboardAppointments.innerHTML = table(dashboard.tables.todays_appointments, [
      { label: "Token", key: "token" },
      { label: "Patient", key: "patient" },
      { label: "Time", render: (row) => formatTime(row.time) },
      { label: "Status", render: (row) => statusBadge(row.status) }
    ]).replace("No records found.", "No appointments scheduled today.");
    recentPrescriptions.innerHTML = table(dashboard.tables.recent_prescriptions, [
      { label: "Patient", key: "patient" },
      { label: "Medicine", key: "medicine" },
      { label: "Doctor", key: "doctor" },
      { label: "Date", render: (row) => formatDateTime(row.date) }
    ]).replace("No records found.", "No prescriptions generated yet.");

    upsertChart("monthlyPatientsChart", "line", dashboard.charts.monthly_patient_registrations, { label: "Patients", backgroundColor: "rgba(37,99,235,.12)", fill: true });
    upsertChart("dailyAppointmentsChart", "bar", dashboard.charts.daily_appointments, { label: "Appointments", backgroundColor: "#69c7f4" });
    upsertChart("appointmentStatusChart", "pie", dashboard.charts.appointment_status_distribution);
    upsertChart("commonDiseasesChart", "bar", dashboard.charts.common_diseases, { label: "Diagnoses", backgroundColor: "#17a99b" });
    upsertChart("medicineUsageChart", "bar", dashboard.charts.medicine_usage, { label: "Prescriptions", backgroundColor: "#2563EB", indexAxis: "y" });
    upsertChart("weeklyConsultationsChart", "line", dashboard.charts.weekly_consultations, { label: "Consultations", backgroundColor: "rgba(23,169,155,.14)", borderColor: "#17a99b", fill: true });
    upsertChart("followupStatusChart", "doughnut", dashboard.charts.followup_status);
    upsertChart("aiActivityChart", "line", dashboard.charts.ai_recommendation_activity, { label: "AI Recommendations", backgroundColor: "rgba(183,121,31,.12)", borderColor: "#b7791f", fill: true });
    dashboardStatus.textContent = `Live dashboard updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    dashboardStatus.classList.remove("error");
  } catch (error) {
    dashboardStatus.textContent = `Dashboard update failed: ${error.message}. Retrying automatically.`;
    dashboardStatus.classList.add("error");
  }
}

async function searchPatients() {
  const q = document.getElementById("patientSearch").value.trim();
  const rows = await api(`/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  patientResults.innerHTML = table(rows, [
    { label: "ID", key: "patient_code" },
    { label: "Name", key: "name" },
    { label: "Phone", key: "phone" },
    { label: "BMI", key: "bmi" },
    { label: "Action", render: (row) => `<button class="mini-btn" data-open-patient="${row.id}" data-patient-label="${escapeHtml(`${row.patient_code} - ${row.name}`)}">Timeline</button>` }
  ]);
}

document.getElementById("searchPatients").addEventListener("click", searchPatients);
document.getElementById("patientResults").addEventListener("click", async (event) => {
  const id = event.target.dataset.openPatient;
  if (!id) return;
  await loadPatientTimeline(id, event.target.dataset.patientLabel);
});
document.getElementById("recentPatients").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-patient]");
  if (!button) return;
  await loadPatientTimeline(button.dataset.patient, button.dataset.patientLabel);
});

document.getElementById("patientForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/patients", { method: "POST", body: JSON.stringify(formJson(event.target)) });
  event.target.reset();
  await searchPatients();
  await loadDashboard();
});

async function loadDoctors() {
  const doctors = await api("/auth/doctors");
  const options = doctors.map((doctor) => `<option value="${doctor.id}">${escapeHtml(doctor.full_name)}${doctor.specialty ? ` - ${escapeHtml(doctor.specialty)}` : ""}</option>`).join("");
  if (appointmentDoctor) appointmentDoctor.innerHTML = `<option value="">Select doctor</option>${options}`;
  if (appointmentDoctorFilter) appointmentDoctorFilter.innerHTML = `<option value="">All doctors</option>${options}`;
}

async function loadAppointmentPatients(q = "") {
  if (!appointmentPatient) return;
  const patients = await api(`/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  appointmentPatient.innerHTML = `<option value="">Select patient</option>${patients.map((patient) => `<option value="${patient.id}">${escapeHtml(patient.patient_code)} - ${escapeHtml(patient.name)}</option>`).join("")}`;
}

async function loadAppointmentSummary() {
  const stats = await api("/appointments/summary");
  apptToday.textContent = stats.todays_appointments;
  apptWaiting.textContent = stats.waiting_patients;
  apptProgress.textContent = stats.in_progress;
  apptCompleted.textContent = stats.completed_today;
  apptCancelled.textContent = stats.cancelled_today;
}

function appointmentQuery() {
  const params = new URLSearchParams();
  params.set("view", appointmentView?.value || "day");
  if (appointmentSearch?.value.trim()) params.set("q", appointmentSearch.value.trim());
  if (appointmentDateFilter?.value) {
    params.set("date_from", appointmentDateFilter.value);
    params.set("date_to", appointmentDateFilter.value);
  }
  if (appointmentDoctorFilter?.value && current.role === "nurse") params.set("doctor_id", appointmentDoctorFilter.value);
  if (appointmentStatusFilter?.value) params.set("status", appointmentStatusFilter.value);
  return params.toString();
}

function renderNurseAppointments(rows) {
  appointmentResults.style.display = "block";
  doctorAppointmentCards.style.display = "none";
  appointmentResults.innerHTML = table(rows, [
    { label: "Token Number", key: "token_number" },
    { label: "Patient ID", key: "patient_code" },
    { label: "Patient Name", key: "patient_name" },
    { label: "Appointment Date", render: (row) => formatDate(row.appointment_date) },
    { label: "Time", render: (row) => formatTime(row.appointment_time) },
    { label: "Doctor", key: "doctor_name" },
    { label: "Visit Type", key: "visit_type" },
    { label: "Priority", key: "priority" },
    { label: "Status", render: (row) => statusBadge(row.status) },
    {
      label: "Actions",
      render: (row) => `
        <button class="mini-btn" data-edit-appointment="${row.id}">Edit</button>
        <button class="mini-btn danger-action" data-delete-appointment="${row.id}">Delete</button>
      `
    }
  ]);
}

function renderDoctorAppointments(rows) {
  appointmentResults.style.display = "none";
  doctorAppointmentCards.style.display = "grid";
  doctorAppointmentCards.innerHTML = rows.map((row) => `
    <article class="appointment-card">
      <div class="appointment-card-head">
        <div>
          <h3>${escapeHtml(row.token_number || `#${row.id}`)} - ${escapeHtml(row.patient_name)}</h3>
          <p>${escapeHtml(row.patient_code)} at ${formatTime(row.appointment_time)}</p>
        </div>
        ${statusBadge(row.status)}
      </div>
      <div class="appointment-meta">
        <span>${escapeHtml(row.visit_type || "-")}</span>
        <span>${escapeHtml(row.priority || "-")}</span>
        <span>${formatDate(row.appointment_date)}</span>
      </div>
      <p>${escapeHtml(row.reason_for_visit || "No reason recorded.")}</p>
      <div class="quick-actions">
        <button class="mini-btn" data-open-appointment-patient="${row.patient_id}" data-patient-label="${escapeHtml(`${row.patient_code} - ${row.patient_name}`)}">Open Patient Record</button>
        <button class="mini-btn" data-start-appointment="${row.id}">Start Consultation</button>
        <button class="mini-btn" data-complete-appointment="${row.id}" data-reason="${escapeHtml(row.reason_for_visit || "")}">Complete Consultation</button>
        <button class="mini-btn danger-action" data-delete-appointment="${row.id}">Delete Appointment</button>
      </div>
    </article>
  `).join("") || "<p class='empty'>No appointments found.</p>";
}

async function loadAppointments() {
  const rows = await api(`/appointments?${appointmentQuery()}`);
  if (current.role === "doctor") renderDoctorAppointments(rows);
  else renderNurseAppointments(rows);
  await loadAppointmentSummary();
}

appointmentPatientSearch?.addEventListener("input", async (event) => {
  await loadAppointmentPatients(event.target.value.trim());
});

document.getElementById("appointmentForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formJson(event.target);
  delete payload.patient_query;
  await api("/appointments", { method: "POST", body: JSON.stringify(payload) });
  event.target.reset();
  await loadAppointmentPatients();
  await loadAppointments();
  await loadDashboard();
  alert("New appointment booked");
});

document.getElementById("filterAppointments")?.addEventListener("click", loadAppointments);

document.getElementById("appointmentResults")?.addEventListener("click", async (event) => {
  const editId = event.target.dataset.editAppointment;
  const deleteId = event.target.dataset.deleteAppointment;
  if (editId) {
    const status = prompt("Update status: waiting, in_progress, completed, cancelled");
    if (!status) return;
    await api(`/appointments/${editId}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await loadAppointments();
    await loadDashboard();
  }
  if (deleteId) {
    if (!confirm("Are you sure you want to delete this appointment? This action cannot be undone.")) return;
    await api(`/appointments/${deleteId}`, { method: "DELETE" });
    await loadAppointments();
    await loadDashboard();
  }
});

document.getElementById("doctorAppointmentCards")?.addEventListener("click", async (event) => {
  const openPatientId = event.target.dataset.openAppointmentPatient;
  const startId = event.target.dataset.startAppointment;
  const completeId = event.target.dataset.completeAppointment;
  const deleteId = event.target.dataset.deleteAppointment;
  if (openPatientId) {
    await loadPatientTimeline(openPatientId, event.target.dataset.patientLabel);
    document.querySelector('[data-view="patients"]').click();
  }
  if (startId) {
    await api(`/appointments/${startId}/start`, { method: "POST", body: JSON.stringify({}) });
    await loadAppointments();
    await loadDashboard();
  }
  if (completeId) {
    const diagnosis = prompt("Diagnosis");
    if (!diagnosis) return;
    const prescription = prompt("Prescription");
    const doctorNotes = prompt("Doctor notes");
    await api(`/appointments/${completeId}/complete`, {
      method: "POST",
      body: JSON.stringify({
        symptoms: event.target.dataset.reason || "Consultation completed from appointment.",
        diagnosis,
        prescription,
        doctor_notes: doctorNotes,
        ai_summary: document.getElementById("aiResult")?.innerText || null
      })
    });
    await loadAppointments();
    await loadDashboard();
    alert("Appointment completed");
  }
  if (deleteId) {
    if (!confirm("Are you sure you want to delete this appointment? This action cannot be undone.")) return;
    await api(`/appointments/${deleteId}`, { method: "DELETE" });
    await loadAppointments();
    await loadDashboard();
  }
});

async function searchMedicines() {
  const q = document.getElementById("medicineSearch").value.trim();
  const rows = await api(`/medicines${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  medicineResults.innerHTML = table(rows, [
    { label: "Name", key: "medicine_name" },
    { label: "Generic", key: "generic_name" },
    { label: "Class", key: "drug_class" },
    { label: "Stock", key: "stock_quantity" },
    { label: "Required", render: (row) => row.prescription_required ? "Yes" : "No" }
  ]);
}

document.getElementById("searchMedicines").addEventListener("click", searchMedicines);
document.getElementById("medicineImport")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = await api("/medicines/import", { method: "POST", body: new FormData(event.target) });
  alert(`Created ${result.created}, updated ${result.updated}, errors ${result.errors.length}`);
  await searchMedicines();
  await loadDashboard();
});

function renderMedicineRecommendations(result) {
  const cards = result.recommendations.map((item) => `
    <article class="medicine-recommendation-card">
      <div class="recommendation-card-head">
        <div>
          <h3>${escapeHtml(item.medicine_name)}</h3>
          <p>${escapeHtml(item.generic_name || "Generic name not recorded")}</p>
        </div>
        <button class="mini-btn" type="button" data-select-medicine="${item.medicine_id}">Select</button>
      </div>
      <section>
        <h4>Why Recommended</h4>
        <p>${escapeHtml(item.why_recommended)}</p>
      </section>
      <section>
        <h4>Medicine Description</h4>
        <p>${escapeHtml(item.medicine_description || "No description stored in the medicine database.")}</p>
      </section>
      <section>
        <h4>Matching Symptoms</h4>
        <div class="symptom-chip-row">${(item.matching_symptoms.length ? item.matching_symptoms : ["No direct keyword match"]).map((symptom) => `<span>&#10003; ${escapeHtml(symptom)}</span>`).join("")}</div>
      </section>
      <section>
        <h4>Uses</h4>
        <p>${escapeHtml(item.uses || "No uses recorded.")}</p>
      </section>
      <section>
        <h4>Warnings</h4>
        <ul>${item.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>
      </section>
    </article>
  `).join("");
  aiResult.innerHTML = `
    <div class="ai-note">${escapeHtml(result.content)}<br><br>${escapeHtml(result.safety_notice)}</div>
    <div class="medicine-recommendation-list">${cards || "<p class='empty'>No matching medicines found in the medicine database.</p>"}</div>
  `;
}

document.getElementById("medicineAiForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!selectedPatientId) {
    aiResult.innerHTML = "<p class='error'>Select a patient from the Patients tab before analyzing medicine recommendations.</p>";
    return;
  }
  const data = formJson(event.target);
  aiResult.textContent = "Ranking medicines...";
  const result = await api("/ai/medicine-recommendations", {
    method: "POST",
    body: JSON.stringify({ patient_id: selectedPatientId, symptoms: data.symptoms })
  });
  renderMedicineRecommendations(result);
});

document.getElementById("aiResult")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-select-medicine]");
  if (!button) return;
  document.querySelectorAll("[data-select-medicine]").forEach((item) => {
    item.classList.remove("selected");
    item.textContent = "Select";
  });
  button.classList.add("selected");
  button.textContent = "Selected";
});

document.querySelectorAll("[data-report]").forEach((button) => {
  button.addEventListener("click", async () => {
    const result = await api(`/reports/summary?period=${button.dataset.report}`);
    reportResult.textContent = JSON.stringify(result, null, 2);
  });
});

document.getElementById("medicineExcel").addEventListener("click", async (event) => {
  event.preventDefault();
  const blob = await api("/reports/medicines.xlsx");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "medicine-report.xlsx";
  link.click();
  URL.revokeObjectURL(url);
});

let activeAssistantConversationId = null;

const assistantSuggestionsByRole = {
  doctor: [
    "Show today's appointments",
    "Find diabetic patients",
    "Search Paracetamol",
    "Show patient PT000012 history",
    "Pending follow-ups"
  ],
  nurse: [
    "Today's registrations",
    "Booked appointments",
    "Search patient",
    "Medicine inventory",
    "Registration statistics"
  ]
};

function markdownToHtml(markdown) {
  const lines = escapeHtml(markdown).split("\n");
  let html = "";
  let inList = false;
  let inTable = false;
  let inCode = false;
  let tableHeaders = [];
  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };
  const closeTable = () => {
    if (inTable) {
      html += "</tbody></table>";
      inTable = false;
      tableHeaders = [];
    }
  };
  lines.forEach((line) => {
    if (line.trim().startsWith("```")) {
      closeList();
      closeTable();
      html += inCode ? "</code></pre>" : "<pre><code>";
      inCode = !inCode;
      return;
    }
    if (inCode) {
      html += `${line}\n`;
      return;
    }
    if (/^\|(.+\|)+$/.test(line.trim())) {
      closeList();
      const cells = line.split("|").slice(1, -1).map((cell) => cell.trim());
      if (cells.every((cell) => /^-+$/.test(cell.replaceAll(" ", "")))) return;
      if (!inTable) {
        tableHeaders = cells;
        html += `<table><thead><tr>${cells.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead><tbody>`;
        inTable = true;
      } else {
        html += `<tr>${cells.map((cell) => `<td>${cell}</td>`).join("")}</tr>`;
      }
      return;
    }
    closeTable();
    if (line.startsWith("### ")) {
      closeList();
      html += `<h3>${line.slice(4)}</h3>`;
      return;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${line.slice(2)}</li>`;
      return;
    }
    closeList();
    if (!line.trim()) return;
    html += `<p>${line}</p>`;
  });
  closeList();
  closeTable();
  if (inCode) html += "</code></pre>";
  return html
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function renderAssistantSuggestions() {
  if (!assistantSuggestions) return;
  const suggestions = assistantSuggestionsByRole[current.role] || assistantSuggestionsByRole.nurse;
  assistantSuggestions.innerHTML = suggestions.map((text) => `<button class="suggestion-card" type="button" data-suggestion="${escapeHtml(text)}">${escapeHtml(text)}</button>`).join("");
}

function renderAssistantMessages(conversation) {
  activeAssistantConversationId = conversation?.id || null;
  assistantTitle.textContent = conversation?.title || "New conversation";
  const messages = conversation?.messages || [];
  assistantMessages.innerHTML = messages.map((message) => `
    <article class="chat-message ${message.role === "user" ? "user" : "assistant"}">
      ${markdownToHtml(message.content)}
      ${message.role === "assistant" && message.data_source ? `<span class="data-source">Data Source: ${escapeHtml(message.data_source)}</span>` : ""}
    </article>
  `).join("") || "<p class='empty'>Start a conversation with the AI Assistant.</p>";
  assistantMessages.scrollTop = assistantMessages.scrollHeight;
}

async function loadAssistantConversations() {
  if (!assistantConversations) return;
  const q = assistantSearch?.value.trim();
  const conversations = await api(`/chat/conversations${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  assistantConversations.innerHTML = conversations.map((item) => `
    <button class="conversation-item ${item.id === activeAssistantConversationId ? "active" : ""}" type="button" data-chat-id="${item.id}">
      <strong>${escapeHtml(item.title)}</strong>
      <span>${escapeHtml(item.last_message || "No messages yet")}</span>
    </button>
  `).join("") || "<p class='empty'>No conversations yet.</p>";
}

async function openAssistantConversation(id) {
  const conversation = await api(`/chat/conversations/${id}`);
  renderAssistantMessages(conversation);
  await loadAssistantConversations();
}

async function startNewAssistantConversation() {
  activeAssistantConversationId = null;
  renderAssistantMessages(null);
  assistantInput.value = "";
  await loadAssistantConversations();
  assistantInput.focus();
}

async function sendAssistantMessage(message) {
  assistantTyping.hidden = false;
  try {
    const payload = { conversation_id: activeAssistantConversationId, message };
    const result = await api("/chat/messages", { method: "POST", body: JSON.stringify(payload) });
    renderAssistantMessages(result.conversation);
    await loadAssistantConversations();
  } finally {
    assistantTyping.hidden = true;
  }
}

renderAssistantSuggestions();

document.getElementById("assistantForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = assistantInput.value.trim();
  if (!message) return;
  assistantInput.value = "";
  assistantMessages.innerHTML += `<article class="chat-message user">${markdownToHtml(message)}</article>`;
  assistantMessages.scrollTop = assistantMessages.scrollHeight;
  await sendAssistantMessage(message);
});

document.getElementById("assistantSuggestions")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-suggestion]");
  if (!button) return;
  assistantInput.value = button.dataset.suggestion;
  assistantInput.focus();
});

document.getElementById("assistantConversations")?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-chat-id]");
  if (!button) return;
  await openAssistantConversation(Number(button.dataset.chatId));
});

document.getElementById("assistantSearch")?.addEventListener("input", loadAssistantConversations);
document.getElementById("newAssistantChat")?.addEventListener("click", startNewAssistantConversation);
document.getElementById("newAssistantChatBottom")?.addEventListener("click", startNewAssistantConversation);
document.getElementById("clearAssistantChat")?.addEventListener("click", () => renderAssistantMessages({ id: activeAssistantConversationId, title: assistantTitle.textContent, messages: [] }));

document.getElementById("renameAssistantChat")?.addEventListener("click", async () => {
  if (!activeAssistantConversationId) return;
  const title = prompt("Conversation title", assistantTitle.textContent);
  if (!title) return;
  const conversation = await api(`/chat/conversations/${activeAssistantConversationId}`, { method: "PATCH", body: JSON.stringify({ title }) });
  renderAssistantMessages(conversation);
  await loadAssistantConversations();
});

document.getElementById("deleteAssistantChat")?.addEventListener("click", async () => {
  if (!activeAssistantConversationId) return;
  if (!confirm("Delete this conversation?")) return;
  await api(`/chat/conversations/${activeAssistantConversationId}`, { method: "DELETE" });
  await startNewAssistantConversation();
});

loadDashboard();
searchPatients();
searchMedicines();
loadDoctors();
loadAppointmentPatients();
loadAppointments();
loadAssistantConversations();
setInterval(loadDashboard, 30000);
