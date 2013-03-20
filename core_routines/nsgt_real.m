function [c,Ls] = nsgt_real(f,g,shift,M)
%NSGT_REAL  Nonstationary Gabor transform for real signals
%   Usage: [c,Ls] = nsgt_real(f,g,shift,M)
% 
%   Input parameters:
%         f         : A real-valued signal to be analyzed (For multichannel
%                     signals, input should be a matrix which each
%                     column storing a channel of the signal).
%         g         : Cell array of frequency side analysis windows
%         shift     : Vector of time shifts
%         M         : Number of frequency channels (optional)
%                     If M is constant, the output is converted to a
%                     matrix
%   Output parameters:
%         c         : Transform coefficients (matrix or cell array)
%         Ls        : Original signal length (in samples)
%
%   Given the cell array *g* of windows and the frequency shift vector 
%   *shift*, this function computes the corresponding nonstationary Gabor 
%   filterbank coefficients for the real-valued vector *f*. 
% 
%   The transform produces phase-locked coefficients in the
%   sense that each window is considered to be centered at
%   0 and the signal itself is shifted accordingly.
%
%   More information can be found at:
%   http://univie.ac.at/nonstatgab/
%

% Author: Nicki Holighaus, Gino Velasco
% Date: 03.03.13

% Check input arguments

if nargin <= 2
    error('Not enough input arguments');
end

[Ls,CH]=size(f);

if Ls == 1
    f = f.';
    Ls = CH;
    CH = 1;
end

if CH > Ls
    disp(['The number of signal channels (',num2str(CH),') is larger than']);
    disp(['the number of samples per channel (',num2str(Ls),').']);
    reply = input('Is this correct? ([Y]es,[N]o)', 's');
    switch reply
        case {'N','n','No','no',''}
            reply2 = input('Transpose signal matrix? ([Y]es,[N]o)', 's');
            switch reply2
                case {'N','n','No','no',''}
                    error('Invalid signal input, terminating program');
                case {'Y','y','Yes','yes'}
                    disp('Transposing signal matrix and continuing program execution');
                    f = f.';
                    X = CH; CH = Ls; Ls = CH; clear X;
                otherwise
                    error('Invalid reply, terminating program');
            end
        case {'Y','y','Yes','yes'}
            disp('Continuing program execution');
        otherwise
            error('Invalid reply, terminating program');
    end
end

N=length(shift);    % The number of time slices

if nargin == 3
    M = zeros(N,1);
    for kk = 1:N
        M(kk) = length(g{kk});
    end
end

if max(size(M)) ==  1
    M = M(1)*ones(N,1);
end

timepos = cumsum(shift)-shift(1); % Calculate positions from shift vector

% A small amount of zero-padding might be needed (e.g. for scale frames)

fill = sum(shift)-Ls;
f = [f;zeros(fill,CH)];

c=cell(N,1); % Initialisation of the result

% The actual transform

for ii = 1:N
    Lg = length(g{ii});
    
    idx = [ceil(Lg/2)+1:Lg,1:ceil(Lg/2)];
    win_range = mod(timepos(ii)+(-floor(Lg/2):ceil(Lg/2)-1),Ls+fill)+1;
    
    if M(ii) < Lg % if the number of frequency channels is too small, aliasing is introduced
        col = ceil(Lg/M(ii));
        temp = zeros(col*M(ii),CH);
        
        temp([end-floor(Lg/2)+1:end,1:ceil(Lg/2)],:) = bsxfun(@times,f(win_range,:),g{ii}(idx));
        
        temp = reshape(temp,M(ii),col,CH);
        c{ii} = squeeze(fftreal(sum(temp,2)));
    else
        temp = zeros(M(ii),CH);
        temp([end-floor(Lg/2)+1:end,1:ceil(Lg/2)],:) = bsxfun(@times,f(win_range,:),g{ii}(idx));
        
        c{ii} = fftreal(temp);
    end
end

 if max(M) == min(M)
     c = cell2mat(c);
     c = reshape(c,floor(M(1)/2)+1,N,CH);
 end

end
