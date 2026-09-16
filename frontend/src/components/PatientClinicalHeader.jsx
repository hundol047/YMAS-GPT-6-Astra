import React from 'react';

// Clinical Header: name/sex/age, MRN, DOB, department+attending (from the most recent Encounter),
// primary diagnosis, allergy status, and latest vitals -- kept to one compact strip per the "don't
// overload a single screen" instruction. `encounters` comes from App.jsx's own fetch of
// GET /patients/{id}/encounters, so this component does no fetching itself.
export default function PatientClinicalHeader({patient,encounters}){
 if(!patient)return null;
 const latest=[...(encounters||[])].sort((a,b)=>(b.started_at||'').localeCompare(a.started_at||''))[0];
 // Vitals are selected by their OWN most recent measured_at across ALL encounters -- not scoped
 // to whichever encounter happens to be latest by started_at. An encounter with no vitals of its
 // own must not hide an earlier encounter's still-current reading.
 const allVitals=(encounters||[]).flatMap(e=>e.vital_signs||[]);
 const latestVital=allVitals.length?[...allVitals].sort((a,b)=>(b.measured_at||'').localeCompare(a.measured_at||'')).at(0):null;
 const sexLabel=patient.sex==='female'?'여':patient.sex==='male'?'남':'미상';
 return <div className="clinical-header">
  <div className="clinical-header-top">
   <div className="clinical-header-name"><b>{patient.name}</b><span>{sexLabel}</span><span>{patient.age}세</span></div>
   <div className="clinical-header-grid">
    <div><small>MRN</small><span>{patient.mrn||'—'}</span></div>
    <div><small>DOB</small><span>{patient.date_of_birth?patient.date_of_birth.replaceAll('-','.'):'—'}</span></div>
    <div><small>진료과</small><span>{latest?.department||'—'}</span></div>
    <div><small>담당의</small><span>{latest?.attending_physician||'—'}</span></div>
    <div className="clinical-header-wide"><small>주요 진단</small><span>{patient.diagnosis||'—'}</span></div>
    <div><small>Allergy</small><span className={patient.allergies?.length?'text-danger':''}>{patient.allergies?.length?patient.allergies.map(a=>a.substance).join(', '):'NKDA'}</span></div>
   </div>
  </div>
  <div className="clinical-header-vitals">
   <div><small>BP</small><b>{latestVital?.sbp&&latestVital?.dbp?`${latestVital.sbp}/${latestVital.dbp}`:'—'}</b></div>
   <div><small>HR</small><b>{latestVital?.heart_rate??'—'}<small>{latestVital?.heart_rate!=null?' bpm':''}</small></b></div>
   <div><small>SpO₂</small><b>{latestVital?.spo2??'—'}<small>{latestVital?.spo2!=null?'%':''}</small></b></div>
  </div>
 </div>;
}
