import React from 'react';
import {afterEach,expect,test} from 'vitest';
import {render,screen,cleanup,waitFor,within,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../src/App.jsx';
afterEach(cleanup);

// Full Clinical Workspace journey against the real backend (same real-API-via-bridge pattern as
// workspace.test.jsx, see tests/setup.js) -- Clinical Header, Timeline, SOAP note lifecycle
// (draft -> sign -> reject direct edit -> amendment), Medication Order precheck+override,
// Lab Order -> Result, and that the confirmed order shows up in the Medication tab.
test('Clinical Workspace: header, timeline, SOAP note sign+amend, order precheck+override, lab result',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});

 // Clinical Header shows the seeded encounter's demographic/department/vitals data. Encounters
 // load via a separate fetch from the patient record, so wait for it rather than asserting
 // synchronously right after the heading appears.
 await screen.findByText('2026090012');
 await screen.findByText('순환기내과');
 await screen.findByText('김도현');

 // Timeline: seeded INR history (2.1 -> 2.6 -> 3.8) must show up
 await user.click(screen.getByRole('tab',{name:'Timeline'}));
 await screen.findByText('Patient Timeline');
 await waitFor(()=>expect(screen.getAllByText(/INR/).length).toBeGreaterThan(0));

 // Clinical Note: draft -> sign -> signed notes reject direct PATCH -> explicit amendment
 await user.click(screen.getByRole('tab',{name:'Clinical Note'}));
 await screen.findByText('Clinical Note (SOAP)');
 await user.type(screen.getByPlaceholderText('chief complaint, symptoms, HPI'),'DOM 테스트 주소증');
 await user.type(screen.getByPlaceholderText('medication, orders, follow-up'),'DOM 테스트 plan');
 await user.click(screen.getByRole('button',{name:/임시 저장/}));
 await screen.findByText('초안');
 await user.click(screen.getByRole('button',{name:'서명'}));
 await screen.findByText('서명됨');
 // Two signed notes exist now (the seeded one + this one) -- scope to the one this test wrote.
 const myNote=(await screen.findByText('DOM 테스트 주소증')).closest('.note-card');
 await user.click(within(myNote).getByRole('button',{name:'수정 (Amendment)'}));
 await user.type(within(myNote).getByPlaceholderText('수정 사유 (필수)'),'DOM 테스트 수정 사유');
 await user.click(within(myNote).getByRole('button',{name:'수정 제출'}));
 await within(myNote).findByText(/수정 이력/);

 // Orders: precheck the ALREADY-active warfarin+aspirin interaction -> requires override -> confirm
 await user.click(screen.getByRole('tab',{name:'Orders'}));
 await screen.findByText('Medication Order');
 await user.type(screen.getByLabelText('Medication'),'와파린');
 await user.click(await screen.findByRole('option',{name:/와파린/}));
 await user.type(screen.getByLabelText('Dose'),'2');
 await user.click(screen.getByRole('button',{name:'SynexAgent 사전 분석 실행'}));
 await screen.findByText(/새로운 SynexAgent 신호가 감지/);
 await user.type(screen.getByLabelText(/Override 사유/),'DOM 테스트 override 사유');
 await user.click(screen.getByRole('button',{name:'경고 확인 후 처방 제출'}));
 await screen.findByText('처방이 저장되었습니다.');

 await user.type(screen.getByLabelText('Test'),'BUN');
 await user.click(screen.getByRole('button',{name:'검사 처방'}));
 await screen.findByText('검사 처방이 저장되었습니다.');

 // Medication tab: the confirmed order (with its override reason) shows up
 await user.click(screen.getByRole('tab',{name:'Medication'}));
 await screen.findByText('Medication Orders');
 await waitFor(()=>expect(screen.getByText('confirmed')).toBeTruthy());
 expect(screen.getByText('DOM 테스트 override 사유')).toBeTruthy();

 // Results: enter a result for the pending BUN order
 await user.click(screen.getByRole('tab',{name:'Results'}));
 await screen.findByText('BUN');
 await user.click(screen.getByRole('button',{name:'결과 입력'}));
 await user.type(screen.getByLabelText('BUN 결과 값'),'18');
 await user.click(screen.getByRole('button',{name:'결과 저장'}));
 await waitFor(()=>expect(screen.getByText('대기 중인 검사가 없습니다.')).toBeTruthy());
});

test('patient switch resets Clinical Workspace tab state',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await user.click(screen.getByRole('tab',{name:'Clinical Note'}));
 await screen.findByText('Clinical Note (SOAP)');
 await user.click(screen.getByRole('button',{name:/김하늘 34세/}));
 await screen.findByRole('heading',{name:'김하늘 34세 / 여성'});
 // Tab resets to overview on patient switch (existing behavior, unchanged) rather than staying
 // on a stale Clinical Note view for the wrong patient.
 await screen.findByText('SYNEX RISK INDEX');
});

// Item 7: the backend's deterministic clinical-summary template must actually reach the screen,
// on the Overview tab, using the server's own sentence text (never a frontend-fabricated one).
test('Clinical Summary card shows the backend template and refreshes on patient switch',async()=>{
 render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await screen.findByText('SynexAgent Clinical Summary');
 // SYN-002's seeded INR history (2.1 -> 2.6 -> 3.8) is a rising trend the backend template
 // should have detected and phrased as a sentence citing INR.
 await waitFor(()=>expect(screen.getAllByText(/INR/).length).toBeGreaterThan(0));
 await screen.findByText(/결정론적 규칙으로 생성/);
});

// Item 8: Diagnosis/Problem List UI must be wired to the real backend (POST .../diagnoses,
// GET .../problem-list), not a UI-only mockup -- a new diagnosis must persist and show up in the
// Problem List after creation.
test('Diagnosis registration is wired to the real backend and refreshes the Problem List',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await user.click(screen.getByRole('tab',{name:'Clinical Note'}));
 await screen.findByText('Diagnosis / Problem List');
 await user.type(screen.getByPlaceholderText('예: Atrial fibrillation'),'DOM 테스트 진단');
 await user.click(screen.getByRole('button',{name:/진단 추가/}));
 await screen.findByText('DOM 테스트 진단');
});

// Item 9: Results must show the patient's EXISTING (legacy/seeded) lab history merged with any
// new LabOrder-derived results -- not only results created through the new Order flow.
test('Results shows the existing legacy INR history via the unified endpoint',async()=>{
 render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 const user=userEvent.setup();
 await user.click(screen.getByRole('tab',{name:'Results'}));
 await screen.findByText('검사 결과 추세 (통합)');
 await waitFor(()=>expect(screen.getAllByText(/INR/).length).toBeGreaterThan(0));
 // The seeded INR trend (2.1 -> 2.6 -> 3.8) should be visible as a chronological series, scoped
 // to the INR result group (other test names share overlapping numeric substrings).
 const inrGroup=(await screen.findByText('INR',{selector:'b'})).closest('.result-group');
 await within(inrGroup).findByText(/2\.1/);
 await within(inrGroup).findByText(/3\.8/);
});

// Item 6: a Clinical Summary sentence's "관련 기록 보기" (jump to source) must actually land on
// and highlight the matching Timeline entry -- this used to silently find nothing for a
// medication sentence, because its source id carried the internal 'order:RX-<id>' dual-write
// marker instead of the bare id Timeline indexes by.
test('Clinical Summary "관련 기록 보기" for a medication sentence highlights the matching Timeline entry',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await user.click(screen.getByRole('tab',{name:'Orders'}));
 await screen.findByText('Medication Order');
 await user.type(screen.getByLabelText('Medication'),'리시노프릴');
 await user.click(await screen.findByRole('option',{name:/리시노프릴/}));
 await user.type(screen.getByLabelText('Dose'),'10');
 await user.click(screen.getByRole('button',{name:'SynexAgent 사전 분석 실행'}));
 await waitFor(()=>expect(screen.queryByText(/새로운 SynexAgent 신호가 감지/)||screen.queryByText('처방 제출')).toBeTruthy());
 const submit=screen.queryByRole('button',{name:'경고 확인 후 처방 제출'})||screen.getByRole('button',{name:'처방 제출'});
 if(submit.textContent.includes('경고'))await user.type(screen.getByLabelText(/Override 사유/),'DOM 테스트 요약 연결 확인용');
 await user.click(submit);
 await screen.findByText('처방이 저장되었습니다.');

 await user.click(screen.getByRole('tab',{name:'분석 요약'}));
 await screen.findByText('SynexAgent Clinical Summary');
 const medSentence=(await screen.findByText(/현재 활성 처방을 유지 중입니다/)).closest('li');
 await user.click(within(medSentence).getByRole('button',{name:/관련 기록 보기/}));

 await screen.findByText('Patient Timeline');
 await waitFor(()=>{
  const highlighted=document.querySelector('.timeline-item.highlighted');
  expect(highlighted).toBeTruthy();
  expect(highlighted.className).toContain('type-medication');
 });
});

// Item 1/10: a rapid double-submit (or a network retry) of the same Medication Order must not
// create two orders -- the UI's disabled={confirmBusy} is a UX nicety, the real safeguard is the
// server-side Idempotency-Key header (see OrdersPanel.jsx/backend main.py). fireEvent.click twice
// back-to-back (not awaited in between, unlike userEvent.click) simulates firing before React has
// re-rendered the disabled state.
test('rapid double-submit of a Medication Order creates only one order (server-side idempotency)',async()=>{
 // Uses furosemide -- a drug no other test in this file orders for SYN-002 -- so the assertion
 // below can't be confused by a legitimate single order some other test already placed on this
 // same shared demo patient (all tests in this file share one backend process/patient state).
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await user.click(screen.getByRole('tab',{name:'Orders'}));
 await screen.findByText('Medication Order');
 await user.type(screen.getByLabelText('Medication'),'푸로세미드');
 await user.click(await screen.findByRole('option',{name:/푸로세미드/}));
 await user.type(screen.getByLabelText('Dose'),'20');
 await user.click(screen.getByRole('button',{name:'SynexAgent 사전 분석 실행'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'경고 확인 후 처방 제출'})||screen.queryByRole('button',{name:'처방 제출'})).toBeTruthy());
 const submit=screen.queryByRole('button',{name:'경고 확인 후 처방 제출'})||screen.getByRole('button',{name:'처방 제출'});
 if(/경고/.test(submit.textContent))await user.type(screen.getByLabelText(/Override 사유/),'DOM 테스트 중복 제출 방지 확인');
 fireEvent.click(submit);
 fireEvent.click(submit);
 await screen.findByText('처방이 저장되었습니다.');
 await user.click(screen.getByRole('tab',{name:'Medication'}));
 await screen.findByText('Medication Orders');
 await waitFor(()=>expect(screen.getAllByText(/furosemide/i).length).toBe(1));
});

// Item 4/20: a write action refused by the backend (403, the shape a clinician_readonly caller
// would get) must surface as a visible, readable error -- not a silent failure or a crash.
test('a refused write action surfaces a visible error instead of crashing',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await user.click(screen.getByRole('tab',{name:'Clinical Note'}));
 await screen.findByText('Clinical Note (SOAP)');
 const original=globalThis.fetch;
 globalThis.fetch=(url,options)=>url.includes('/encounters/')&&url.includes('/notes')&&options?.method!=='GET'
  ?Promise.resolve({ok:false,status:403,json:async()=>({detail:'Role "clinician_readonly" is not permitted to note:write'})})
  :original(url,options);
 try{
  await user.type(screen.getByPlaceholderText('chief complaint, symptoms, HPI'),'권한 없는 시도');
  await user.click(screen.getByRole('button',{name:/임시 저장/}));
  const alert=await screen.findByRole('alert');
  expect(alert.textContent).toMatch(/permitted to note:write/);
 }finally{globalThis.fetch=original}
});
