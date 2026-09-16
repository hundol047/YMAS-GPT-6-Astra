import React from 'react';
import {afterEach,expect,test} from 'vitest';
import {render,screen,cleanup,waitFor,within} from '@testing-library/react';
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
