import React from 'react';
import {afterEach,expect,test} from 'vitest';
import {render,screen,waitFor,cleanup,within,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../src/App.jsx';
afterEach(cleanup);
test('real FastAPI app: analysis, patient switch, simulation, review and persistent audit',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByRole('heading',{name:'박도윤 72세 / 남성'});
 await screen.findByText('HIGH · 모델 고위험');
 expect(screen.getByText('95.3')).toBeTruthy();
 const interaction=screen.getByRole('button',{name:/아스피린 \+ 와파린/});await user.click(interaction);
 const dialog=screen.getByRole('dialog');
 await user.type(within(dialog).getByLabelText('판단 근거 또는 확인 내용'),'DOM 통합 테스트: 원처방 검토');
 await user.click(within(dialog).getByRole('button',{name:'확인',exact:true}));
 await screen.findByText('검토 기록을 저장했습니다. 처방은 변경되지 않았습니다.');
 await user.click(within(dialog).getByRole('button',{name:'경고 상세 닫기'}));
 await user.click(screen.getByRole('tab',{name:/검토 이력/}));
 await screen.findAllByText('DOM 통합 테스트: 원처방 검토');
 await user.click(screen.getByRole('button',{name:/김하늘 34세/}));
 await screen.findByText('LOW · 모델 저위험');
 expect(screen.getByText('<0.1')).toBeTruthy();
 await user.selectOptions(screen.getByLabelText('추가 약물'),'warfarin');
 await user.click(screen.getByRole('button',{name:'위험 비교'}));
 await screen.findByText('와파린 추가');
 await screen.findByText(/원래 처방 유지/);
 await user.click(screen.getByRole('tab',{name:'진료 기록'}));
 expect(screen.getByRole('cell',{name:'비타민D vitamind'})).toBeTruthy();
 expect(screen.queryByRole('cell',{name:/와파린/})).toBeNull();
});
test('search, rapid patient selection and reset preserve patient identity',async()=>{
 const user=userEvent.setup();render(<App/>);
 await screen.findByText('HIGH · 모델 고위험');
 await user.type(screen.getByLabelText('환자 검색'),'없는환자');
 expect(screen.getByText('검색 결과가 없습니다.')).toBeTruthy();
 await user.clear(screen.getByLabelText('환자 검색'));
 fireEvent.click(screen.getByRole('button',{name:/정수아 46세/}));
 fireEvent.click(screen.getByRole('button',{name:/김하늘 34세/}));
 await screen.findByText('LOW · 모델 저위험');
 expect(screen.getByRole('heading',{name:'김하늘 34세 / 여성'})).toBeTruthy();
 expect(screen.queryByText('중증 약물 반응 이력')).toBeNull();
 await user.click(screen.getByRole('button',{name:'다시 분석'}));
 await screen.findByText('LOW · 모델 저위험');
});
test('failed request is visible and retry recovers',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=(url,options)=>url==='/api/patients'?Promise.reject(new Error('테스트 연결 실패')):original(url,options);
 try{
  const user=userEvent.setup();render(<App/>);
  await screen.findByRole('alert');
  expect(screen.getByRole('alert').textContent).toContain('테스트 연결 실패');
  globalThis.fetch=original;
  await user.click(screen.getByRole('button',{name:'다시 시도'}));
  await screen.findByText('HIGH · 모델 고위험');
  expect(screen.queryByRole('alert')).toBeNull();
 }finally{globalThis.fetch=original}
});
