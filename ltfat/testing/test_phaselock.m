function test_failed=test_phaselock
%TEST_PHASELOCK  Test phaselock and phaseunlock
%

test_failed=0;

disp(' ===============  TEST_PHASELOCK ================');

% set up parameters
L=420;
f=tester_rand(L,1);
g=pgauss(L);
a=10;b=30;M=L/b;

c = dgt(f,g,a,M);
cp1 = ref_phaselock(c,a);
cp2 = phaselock(c,a,'lt',[0 1]);

% compare original phaselock with mine for rectangular case
res=norm(cp1-cp2,'fro');
[test_failed,fail]=ltfatdiditfail(res,test_failed);
fprintf(['PHASELOCK REF RECT %0.5g %s\n'],res,fail);

% comparisons for non-separable case
c_big = dgt(f,g,a,2*M);
c_quin = dgt(f,g,a,M,'lt',[1 2]);

c_bigp = phaselock(c_big,a);
c_quinp= phaselock(c_quin,a,'lt',[1 2]);

% compare the quincunx lattice with twice transform on twice as many
% chanels
res=norm(c_bigp(1:2:end,1)-c_quinp(:,1),'fro');
[test_failed,fail]=ltfatdiditfail(res,test_failed);
fprintf(['PHASELOCK QUIN 1   %0.5g %s\n'],res,fail);

res=norm(c_bigp(2:2:end,2)-c_quinp(:,2),'fro');
[test_failed,fail]=ltfatdiditfail(res,test_failed);
fprintf(['PHASELOCK QUIN 2   %0.5g %s\n'],res,fail);

% testing of phaseunlock routine
res=norm(c_big - phaseunlock(c_bigp,a),'fro');
[test_failed,fail]=ltfatdiditfail(res,test_failed);
fprintf(['PHASEUNLOCK RECT   %0.5g %s\n'],res,fail);

res=norm(c_quin - phaseunlock(c_quinp,a,'lt',[1 2]),'fro');
[test_failed,fail]=ltfatdiditfail(res,test_failed);
fprintf(['PHASEUNLOCK QUIN   %0.5g %s\n'],res,fail);

