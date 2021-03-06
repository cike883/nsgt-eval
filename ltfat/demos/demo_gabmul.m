%DEMO_GABMUL  Time-frequency localization by a Gabor multiplier
%
%   This script creates several different time-frequency symbols
%   and demonstrate their effect on a random, real input signal.
%
%   .. figure::
%
%      Cut a circle in the TF-plane
%
%      This figure shows the symbol (top plot, only the positive frequencies are displayed),
%      the input random signal (bottom) and the output signal (middle).
%
%   .. figure::
%
%      Keep low frequencies (low-pass)
%
%      This figure shows the symbol (top plot, only the positive frequencies are displayed),
%      the input random signal (bottom) and the output signal (middle).
%
%   .. figure::
%
%      Keep middle frequencies (band-pass)
%
%      This figure shows the symbol (top plot, only the positive frequencies are displayed),
%      the input random signal (bottom) and the output signal (middle).
%

disp('Type "help demo_gabmul" to see a description of how this demo works.');

% Setup some suitable parameters for the Gabor system
L=480;
a=20;
M=24;

b=L/M;
N=L/a;

% Plotting initializations
t_axis = (0:(M-1))*a;
f_max = floor(N/2)-1;
f_range = 1:(f_max+1);
f_axis = f_range*b;

xlabel_angle = 7;
ylabel_angle = -11;

% Create a tight window, so it can be used for both analysis and
% synthesis.
g=gabtight(a,M,L);

% Create the random signal.
f=randn(L,1);

% ------- sharp cutoff operator ---------
% This cuts out a circle in the TF-plane. 
symbol1=zeros(M,N);

for m=0:M-1
  for n=0:N-1
    if (m-M/2)^2+(n-N/2)^2 <(M/4)^2
      symbol1(m+1,n+1)=1;
    end;
  end;
end;

% The symbol as defined by the above loops is centered such
% that it keeps the high frequencys. To obtain the low ones, we
% move the symbol along the first dimension:
symbol1=fftshift(symbol1,1);


% Do the actual filtering
ff1=gabmul(f,symbol1,g,a);


% plotting
figure(1);

subplot(3,1,1);
mesh(t_axis,f_axis,symbol1(f_range,:));

if isoctave
  xlabel('Time');
  ylabel('Frequency');
else
  xlabel('Time','rotation',xlabel_angle);
  ylabel('Frequency','rotation',ylabel_angle);
end;

subplot(3,1,2);
plot(real(ff1));

subplot(3,1,3);
plot(f);


% ---- Tensor product symbol, keep low frequencies.
t1=pgauss(M);
t2=pgauss(N);

symbol2=fftshift(t1*t2',2);

% Do the actual filtering
ff2=gabmul(f,symbol2,g,a);


figure(2);

subplot(3,1,1);
mesh(t_axis,f_axis,symbol2(f_range,:));

if isoctave
  xlabel('Time');
  ylabel('Frequency');
else
  xlabel('Time','rotation',xlabel_angle);
  ylabel('Frequency','rotation',ylabel_angle);
end;

subplot(3,1,2);
plot(real(ff2));

subplot(3,1,3);
plot(f);

% ----- Tensor product symbol, keeps middle frequencies.
t1=circshift(pgauss(M,.5),round(M/4))+circshift(pgauss(M,.5),round(3*M/4));
t2=pgauss(N);

symbol3=fftshift(t1*t2',2);

% Do the actual filtering
ff3=gabmul(f,symbol3,g,a);


figure(3);

subplot(3,1,1);
mesh(t_axis,f_axis,symbol3(f_range,:));

if isoctave
  xlabel('Time');
  ylabel('Frequency');    
else    
  xlabel('Time','rotation',xlabel_angle);
  ylabel('Frequency','rotation',ylabel_angle);
end;

subplot(3,1,2);
plot(real(ff3));

subplot(3,1,3);
plot(f);
