#!/usr/bin/env python

import datetime,numbers,warnings,re,copy,weakref,os,calendar


DEBUG=False

def dbg(*args):
    if not DEBUG: return
    print "##DEBUG: ",
    for i in args:
        print i,
    print ""

def list_to_str(listy,spaces=' ',combiner=',',conjunction='and'):
    if not listy:
        return ''
    if not spaces: spaces=''
    if not combiner: combiner=''
    if not conjunction: conjunction=''
    if len(listy)>2:
        if len(listy)==2:
            ret += listy[0]+spaces
        else:
            for e in listy[:-1]:
                ret += '{0}{1}{2}'.format(e,combiner,spaces)
        ret += '{0}{1}'.format(conjunciton,spaces)
    ret+='{}'.format(listy[-1])
    return ret

class Grade(object):
    """A single Grade for assignment/test/etc. 
    
    There are multiple ways to implement this class. To attempt to account 
    for the many methods of calculation, a Grade instance can be configured
    as a unit within a Category instance, or independent; in either case,
    it is held within a Gradebook (through a Category or directly), and
    can have (or not have) any of the attributes listed below. 
    -
    * IMPLEMENTATION 1: Category Element
        If a Grade is used as an element in a Category, it will still
        control it's `score' attribute, but it's weight and/or maximum
        *can* be controlled by the parent Category. As a Category element,
        a Grade can also be "dropped" for calculations, and can be 
        generally better controlled.
    * IMPLEMENTATION 2: Independent
        If a Grade is independent, it must be configured independently.
        It can still be controlled by the gradebook based on it's
        identifiers, but these as well must be configured for each Grade
        that uses this implementations.
    * IMPLEMENTATION n: 
        However you want to implement it!
    -
    ATTRIBUTES:
        name        Human-readable identifier. Ex: 'HW 6'. Must be hashable
        score       Points earned relative to the maximum. Should be a
                        numeric value, or None if not graded.
        maximum     Points possible. Value depends on course and how
                        one chooses to implement the Grade.
        weight      Multiplier to make 'maximum' match the ultimate value
                        of the Grade. Can be handled by parent Category
                        if one exists. [Default=1]
        extra_credit Boolean. If True, max is not added to the total max
                        of the Grade's parents.
        overrides   (Only if Grade is a Category element.) Set of 
                        attributes (strings) to protect from the parent 
                        Category that would (if configured as such) usually
                        do so.
                        Changes made via Grade.mod_overrides function.
        timestamp   For use by external resources. (datetime.datetime)
        identifiers Dictionary of values defined as needed. Useful for
                        attaching Grades to external resources.
    """
    def __init__(self,name,**kwargs):
        object.__init__(self)
        self.name = name
        self.parent = kwargs.get('parent',None)
        self.score = kwargs.get('score',None)
        self.maximum = kwargs.get('maximum',None)
        self.weight = kwargs.get('weight',1)
        self.overrides = kwargs.get('overrides',set())
        if not isinstance(self.overrides,set):
            if isinstance(self.overrides,list):
                self.overrides = set(self.overrides)
            else: self.overrides = set()
        self.timestamp = kwargs.get('timestamp',None)
        if not isinstance(self.timestamp,datetime.datetime):
            if not isinstance(self.timestamp,numbers.Real):
                self.timestamp = None
            else:
                self.timestamp = datetime.datetime.utcfromtimestamp(self.timestamp)
        self.identifiers = kwargs.get('identifiers',{})
        self.extra_credit = kwargs.get('extra_credit',False)
        
        self.inited=True
    
    def mod_overrides(self,remove=False,*args):
        if type(remove) is not bool and remove in self.__dict__:
            args.append(remove)
            remove=False
        for arg in args:
            arg=str(arg.lower())
            if arg not in self.__dict__:
                err = '\'%s\' cannot be overridden because it is not an ' \
                        'attribute.'%arg
                raise KeyError(err)
            if arg in ['parent','overrides']:
                continue
            if remove:
                self.overrides.discard(arg)
            else:
                self.overrides.add(arg)
    
    def __str__(self):
        stry = '{0}.{1}('.format(self.__module__,self.__class__.__name__)
        stry+= 'name={!r},'.format(self.name)
        stry+= 'parent={!r},'.format('None' if not self.parent else '%s'%self.parent.name)
        stry+= 'score={},'.format(self.score)
        if self.extra_credit:
            stry+= 'EXTRA-CREDIT,'
        if self.getMaximum()!=self.maximum and self.parent: 
            stry+='(overridden)maximum={},'.format(self.maximum)
            stry+='(inherited)maximum={},'.format(self.getMaximum())
        else:
            stry+= 'maximum={},'.format(self.getMaximum())
        if self.getWeight()!=self.weight and self.parent: 
            stry+='(overridden)weight={},'.format(self.weight)
            stry+='(inherited)weight={},'.format(self.getWeight())
        else:
            stry+= 'weight={},'.format(self.getWeight())
        perc = self.getPercent()
        if perc is not None:
            stry+= 'percentage={:0.2%},'.format(perc)
        else:
            stry+= 'percentage=N/A,'
        if isinstance(self.timestamp,datetime.datetime):
            stry+= 'timestamp={0:%Y}-{0:%m}-{0:%d} {0:%H}:{0:%M}:{0:%S},'.format(self.timestamp)
        else:
            stry+= 'timestamp=None,'
        stry+= 'overrides('
        if not self.overrides:
            stry+= 'None '
        for i in self.overrides:
            stry+='{!r},'.format(i)
        stry = stry[:-1]+'),'
        stry+= 'identifiers={'
        if not self.identifiers:
            stry+='None,'
        for i in self.identifiers:
            stry+='{!r}={!r},'.format(i,self.identifiers[i])
        stry = stry[:-1]+'}'
        stry+= ').'
        return stry
    
    def getWeight(self):
        if self.parent and 'weight' not in self.overrides and \
                    self.parent.controls_weight and self.\
                    parent.get_grade_weight():
            return self.parent.get_grade_weight()
        return self.weight
    
    def getMaximum(self):
        if self.parent and 'maximum' not in self.overrides and \
                    hasattr(self.parent,'controls_maximum') and \
                    self.parent.controls_maximum:
            return self.parent.get_grade_maximum()
        return self.maximum
    
    def getPercent(self):
        """If both score and maximum are Numeric and maximum is non-zero,
            returns (1.0*score/maximum)"""
        if isinstance(self.score,numbers.Number) and self.getMaximum():
            return (1.0*self.score/self.getMaximum())
        return None
    
    def __setattr__(self,name,value):
        if name != 'overrides' or 'inited' not in self.__dict__:
            object.__setattr__(self,name,value)
    
    def __deepcopy__(self,memo={}):
        ma_dict = dict(self.__dict__)
        ma_dict['overrides'] = copy.deepcopy(ma_dict['overrides'],memo)
        ma_dict['identifiers']=copy.deepcopy(ma_dict['identifiers'],memo)
        name=copy.deepcopy(ma_dict.pop('name'))
        ma_dict['weight']=self.getWeight()
        ma_dict['maximum']=self.getMaximum()
        copeh = Grade(name,**ma_dict)
        return copeh
    
    def __eq__(self,other):
        if not isinstance(other,Grade):
            return False
        for i in ['name','score','overrides','identifiers']:
            x = object.__getattribute__(self,i)
            y = object.__getattribute__(other,i)
            if not (x == y or (x!=0 and y!=0 and not x and not y)):
                return False
        if self.getWeight() != other.getWeight():
            return False
        if self.getMaximum() != other.getMaximum():
            return False
        return True
    
    def compare(self,op,key,VALUE):
        attr=None
        if key in ['weight','maximum','percent']:
            if key == 'weight':  attr=self.getWeight()
            if key == 'maximum': attr=self.getMaximum()
            if key == 'percent': attr=self.getPercent()
        else:
            try:
                attr = object.__getattribute__(self,key)
            except AttributeError:
                return False
        
        attr_type = type(attr)
        val_type = type(VALUE)
        if key == 'overrides' and val_type is list:
            VALUE = set(VALUE)
            val_type = set
        if op in ['GT','GTE','LT','LTE']:
            if (attr_type is None)^(val_type is None): pass
            elif (attr_type is set)^(val_type is set): return False
            elif (attr_type is dict)^(val_type is dict): return False
            
        if not op:
            if not attr and not VALUE:
                return True
            return (attr is VALUE or attr==VALUE)
        elif op=='N':
            if bool(attr)^bool(VALUE):
                return True
            return not (attr is VALUE or attr==VALUE)
        elif op=='GT':
            if attr > VALUE:
                return True
        elif op=='GTE':
            if not attr and not VALUE:
                return True
            if attr >= VALUE:
                return True
        elif op=='LT':
            if attr < VALUE:
                return True
        elif op=='LTE':
            if not attr and not VALUE:
                return True
            if attr <= VALUE:
                return True
        elif op=='BTWN':
            if val_type is not tuple or len(val_type) < 2:
                return False
            if VALUE[0] < attr < VALUE[1]:
                return True
        elif op in ['IN','NIN']:
            try:
                if (op!='IN')^(VALUE in attr):
                    return True
            except:
                return False
        return False

class _gradelist_for_Category(object):
    def __init__(self,parentCategory):
        object.__init__(self)
        self.parentCategory=parentCategory
        self._grades = set()
        self.add_grade = self.add = self.add_grades
        self.remove_grade = self.remove = self.remove_grades
    
    def add_grades(self,docopy=False,*grades):
        if type(docopy) is Grade:
            grades = [docopy]+list(grades)
            docopy=False
        errList=[]
        for gr in grades:
            if type(gr) is Grade:
                if self.parentCategory.parent:
                    if gr in self.parentCategory.parent._Gradebook__weakgradeset:
                        errList.append(gr.name)
                        continue
                elif gr.name in self:
                    errList.append(gr.name)
                    continue
                if docopy:
                    gr = copy.deepcopy(gr)
                gr.parent=self.parentCategory
                self._grades.add(gr)
                if type(self.parentCategory.parent) is Gradebook:
                    self.parentCategory.parent._Gradebook__weakgradeset.add(gr)
        if errList:
            err = 'Attempt to add Grade(s) named '
            err += list_to_str(errList)
            err+=' failed. Names already in Gradebook or gradelist.'
            raise NameError,err
    
    def remove_grades(self,*grades):
        rem_list=[]
        allgone=True
        for gr in self._grades:
            if any([True for x in grades if gr==x or gr.name==x]):
                rem_list.append(gr)
            else:
                allgone=False
        for i in rem_list:
            self._grades.remove(i)
        if not allgone:
            return False
        return True
    
    def isin(self,grade_obj):
        """Checks if a specific Grade instance is in the gradelist"""
        return bool(grade_obj in self._grades)
    
    def __contains__(self,x):
        """Checks if a Grade OR Grade name is in the gradelist by equality.
        
        !!Will return True if gradelist includes a COPY of a Grade,
            not just the exact instance!!
        To check for an exact object, use isin() function.
        """
        dbg('_gradelist[..].__contains__(',x,')')
        nems = self._grades #assuming x is a Grade
        if not isinstance(x,Grade): 
            #probably looking for a name!
            nems = [q.name for q in self._grades]
        dbg('_gradelist[..].__contains__.nems = ',*nems)
        for i in nems:
            if x==i:
                return True
        return False
    
    def __iter__(self):
        return iter(self._grades)
    
    def get_grade(self,gr_name):
        for gr in self._grades:
            if gr.name == gr_name:
                return gr
        return None
    
    def __getitem__(self,key):
        gr = self.get_grade(key)
        if not gr:
            raise KeyError, 'Grade name \'{}\' not in gradelist'.format(key)
        return gr
    
    def get_stat(self,stat,**kwargs):
        """Get information about the Category's Grades.
        
        args:
            stat        ( elem[ent]s | score | max[imum] | points | weights )
        kwargs:
            weighted    Boolean. Should weight factor into calculating stat.
            counted     Boolean. if True and Category.use_best_count, only 
                            looks at the highest N grades (where N is 
                            elements_counted)
        """
        stat=stat.lower()
        if stat.startswith('elem'):     stat = 0#'elements'
        elif stat=='score':             stat = 1#'score'
        elif stat.startswith('max'):    stat = 2#'maximum'
        elif stat.startswith('point'):  stat = 3#'points'
        elif stat.startswith('weight'): stat = 4#'weights'
        else: raise ValueError, '{} is not an accepted argument for stat'.format(stat)
        weighted = kwargs.get('weighted',False)
        counted = kwargs.get('counted',False)
        weighted,counted = map(bool,[weighted,counted])
        
        #generating ordered list of grades
        listy = []
        for gr in self._grades:
            val=None
            if gr.score is not None:
                val=gr.score
                if gr.getMaximum():
                    val/=1.0*gr.getMaximum()
                if gr.getWeight() and weighted:
                    val*=gr.getWeight()
            listy.append( (gr,val) )
        
        listy.sort(lambda a,b: cmp(a[1],b[1]),None,True)
        
        #trimming list (if counted)
        if counted and self.parentCategory.use_best_count and \
                        self.parentCategory.element_count is not None:
            listy = listy[0:self.parentCategory.element_count]
        listy = [x[0] for x in listy]
        
        if stat is 0:
            return listy
        
        #building current score, maximum, points, and weight
        curScore = 0
        curMax = 0
        curPoints = 0
        curWeight = 0
        for gr in listy:
            if gr.score is None:
                continue
            scr,mx,wgt,xtra = gr.score,gr.getMaximum(),gr.getWeight(),gr.extra_credit
            if wgt and weighted:
                scr=scr*wgt
            if mx:
                if weighted:
                    curMax += mx*wgt
                else: curMax += mx
                curPoints+= 1.0*scr/mx
            else:
                curPoints+= scr
            if not xtra:
                curWeight+=wgt
            curScore += scr
        
        if stat is 1:
            return curScore
        if stat is 2:
            return curMax
        if stat is 3:
            if curMax:
                return 1.0*curPoints
            return None
        if stat is 4:
            return curWeight
    
    def identifier_select(self,**kwargs):
        if not kwargs:
            return None
        working_set=set()
        for gradeobj in self._grades:
            isGood=True
            for kw in kwargs:
                if not isGood or not (kw in gradeobj.identifiers and gradeobj.identifiers[kw]==kwargs[kw]):
                    isGood=False
            if isGood is True:
                working_set.add(gradeobj)
        if not working_set:
            return None
        return working_set
    
    def select(self,docopy=False,aslist=False,**kwargs):
        """Retrieves Grades from gradelist according to kwargs.
        
        If multiple kwargs are provided, all will be required for a Grade
        to be returned. 
        Returns None if no matches were found.
        -
        KWARGS:
        Keyword keys can be any of the Grade attributes or any of the 
        following special cases:
            KEY:        RETRIEVES:                                  NOTES
            attr        all Grades where 'attr' is VALUE or ==VALUE
            Nattr       all Grades where 'attr' is not VALUE
            GTattr      all Grades with 'attr' greater-than VALUE   [N,S]
            LTattr      all Grades with 'attr' less-than VALUE      [N,S]
            GTEattr         ''  greater-that-or-equal-to VALUE      [N,S]
            LTEattr         ''  less-than-or-equal-to VALUE         [N,S]
            BTWNattr        ''  with VALUE1 < 'attr' < VALUE2       [N,1]
            INattr          ''  with VALUE in 'attr'              [S,L,D]
            NINattr         ''  with VALUE not in 'attr'          [S,L,D]
        -
        * attr represents the attribute searched-for, e.g. they keyword pair
            'GTscore=12' would match all Grades with scores greater than 12.
        * VALUE represents the keyword value in the keyword pair.
        -
        NOTES:
            [1] Value must be a Tuple, (VALUE1,VALUE2)
            [N] Works for numeric attributes
            [S] Works for string attributes
            [L] Works for list/set attributes
            [D] Works for dict/mapping attributes
        """
        OP_LIST = [None,'N','GT','LT','GTE','LTE','BTWN','IN','NIN']
        reggy = re.compile('^(?P<op>[A-Z]+)?(?P<attr>[a-z_]+)$')
        working_set = set()
        if 'docopy' in kwargs:
            docopy = kwargs['docopy']
            del kwargs['docopy']
        if 'aslist' in kwargs:
            aslist = kwargs['aslist']
            del kwargs['aslist']
        
        op_attr_value = []
        for kw in kwargs:
            reggy_res = reggy.match(kw)
            if not reggy_res: 
                raise ValueError,'Keyword in _gradelist[..].select invalid: %s'%kw
                return None
            op = reggy_res.group('op')
            attr = reggy_res.group('attr')
            if op not in OP_LIST:
                raise ValueError,'%s is not a valid operator.\nOperators: %s'%(op,OP_LIST)
                return None
            op_attr_value.append( (op,attr,kwargs[kw]) )
        for gradeobj in self._grades:
            isGood=True
            for op_set in op_attr_value:
                if isGood and not gradeobj.compare(op_set[0],op_set[1],op_set[2]):
                    isGood=False
            if isGood:
                if docopy:
                    gradeobj = copy.deepcopy(gradeobj)
                working_set.add(gradeobj)
        if working_set and aslist:
            return list(working_set)
        elif working_set:
            return working_set
        return None

class Category(object):
    """A grouping of Grades that can help organize and modify scores.
    
    ATTRIBUTES:
        name            Name of the Category.
        controls_weight Boolean. Set to True if Category controls the
                            weights of its Grade elements.
        grade_weight    If controls_weight is set, this is used as the 
                            weight of each Grade. This is relative to the 
                            *ultimate* course total points. Alternatively,
                            use cat_weight to affect the Category total
                            rather than individual Grades.
        controls_maximum  Boolean. See 'controls_weight'.
        grade_maximum   If controls_maximum is set, this is the maximum of 
                            each Grade.
        cat_weight      Weight of the Category in the course total. Takes
                            priority over 'grade_weight'. None if unused.
        element_count   Ultimate number of elements that will be in the 
                            Category. Used in combination with weight to
                            determine weighted Category total.
        use_best_count  Boolean. If set, element_count represents the number
                            of Grades that will be summed, starting with the
                            highest-scoring. Used if low grades are dropped.
                            If set and element_count is negative, the lowest
                            N scores will be dropped.
    -
    NOTE: By default, this class is in 'SECURE' mode, which refers to the
        basic protections/restrictions on accessing/modifying attributes.
        To disable SECURE mode, change the local variable 'SECURE' in the
        __init__ function to 'False'.
        (The name 'SECURE' DOES NOT express any sort of promise of security, 
        and no security will be promised. The restrictions provided are only
        intended to prevent accidental changes.)
    """
    #Alternatives: Have different implementation settings, such as:
    #  * 
    def __init__(self,cat_name,**kwargs):
        
        #############
        SECURE=True##
        #############
        
        object.__init__(self)
        object.__setattr__(self,'inited',False)
        self.name = cat_name
        parent = kwargs.get('gradebook',kwargs.get('parent',None))
        if not isinstance(parent,Gradebook):
            parent=None
        self.parent = parent
        controls_weight = kwargs.get('controls_weight',False)
        grade_weight = kwargs.get('grade_weight',None)
        controls_maximum = kwargs.get('controls_maximum',False)
        grade_maximum = kwargs.get('grade_maximum',None)
        cat_weight = kwargs.get('cat_weight',None)
        element_count = kwargs.get('element_count',None)
        use_best_count = kwargs.get('element_count',False)
        self.__attribs = {  'controls_weight':  controls_weight,
                            'grade_weight':     grade_weight,
                            'controls_maximum': controls_maximum,
                            'grade_maximum':    grade_maximum,
                            'cat_weight':       cat_weight,
                            'element_count':    element_count,
                            'use_best_count':   use_best_count
                        }
        
        self.grades = _gradelist_for_Category(self)
        
        self.inited=SECURE
    
    def ___Category__x_(s,**a): #p->pref;upref
        if a and a.keys()[0][0] == 'p':return lambda z: '_%s%s'%(type(s)\
        .__name__,z);return lambda z: z[len('_'+type(s).__name__+'__'):]\
        if z.startswith('_'+type(s).__name__+'__') else z[2:] if \
        z.startswith('__') else z
    
    def __setattr__(self,name,value):
        if not object.__getattribute__(self,'inited'):
            object.__setattr__(self,name,value)
        
        elif object.__getattribute__(self,'inited'):
            
            undundSecret = {'__attribs'}
            undundSecret |= set(map(self.___Category__x_(priv=1),undundSecret))
            if name in ['name','parent'] and object.__getattribute__(self,name):
                warnings.warn('Category {} is set at initializatio'\
                                            'n.'.format(name),stacklevel=2)
                return
            if name == 'parent':
                object.__setattr__(self,name,value)
                return
            if name == 'inited':
                warnings.warn('\'inited\' is an internal class attribute.' \
                                                                ,stacklevel=2)
                return
            if name in undundSecret:
                wrn='\'{}\' must be modified by relevant functions of ' \
                    'the class.'.format(self.___Category__x_(QT=3.14)(name))
                warnings.warn(wrn,stacklevel=1)
                return
            if name in ['controls_weight','controls_maximum','use_best_count']:
                value = bool(value)
            elif name in ['grade_weight','grade_maximum','cat_weight']:
                if not (isinstance(value,numbers.Number) or value is None):
                    raise TypeError,'%s must be numeric or None.'%name
                if value is not None: value=float(value)
            elif name in ['element_count']:
                if not (isinstance(value,int) or value==float('inf') or \
                                                value is None):
                    raise TypeError,'%s must be an integer, None, or (I ' \
                        'suppose) infinity.'%name
                if isinstance(value,int): value=int(value)
            else:
                raise AttributeError,'Cannot set \'%s\' of \'%s\' object'% \
                                     (name,type(self).__name__)
            x = object.__getattribute__(self,self.___Category__x_(plot='no')('__attribs'))
            if name not in x:
                return
            object.__getattribute__(self,self.___Category__x_(previous=True)('__attribs'))[name]=value
    
    def get_grade_weight(self):
        """Returns weight of Grades in Category, assuming control."""
        atr = self.__attribs
        if atr['controls_weight'] and (atr['cat_weight'] and atr['element_count'] or atr['grade_weight']):
            if atr['cat_weight'] and atr['element_count']:
                return 1.0*atr['cat_weight']/atr['element_count']
            return atr['grade_weight']
        return False
    
    def __getattribute__(self,name):
        #safe/immutable (should return attribute with no question)
        if name in ['info','name','__class__','__doc__','__module__','grades',
                    '__weakref__','__hash__','_Category___Category__x_',
                    'get_grade_weight','parent']:
            return object.__getattribute__(self,name)
        #specials (should return COPIES)
        if name in ['__dict__']:
            x = object.__getattribute__(self,name)
            return copy.deepcopy(x)
        #attribute getters
        if name in ['get_grade_maximum']:
            exx = self.__attribs[name[4:]]
            return lambda: exx
        intde = object.__getattribute__(self,'inited')
        atrbs = self.___Category__x_(pr1nt=0)('__attribs')
        
        if not intde:
            return object.__getattribute__(self,name)
        if name == 'inited':
            return bool(intde)
        if name == atrbs or name == '__attribs':
            return copy.deepcopy(object.__getattribute__(self,atrbs))
        if name in object.__getattribute__(self, atrbs):
            return object.__getattribute__(self, atrbs)[name]
        else:
            raise AttributeError,'\'%s\' object has no attribute \'%s\''% \
                                 (type(self).__name__,name)
    
    


class Gradebook(object):
    def __init__(self,name,user,**kwargs):
        self.name = name
        self.user = user
        default_dict = {'identifiers':{},
                        
                    }
        not_deflt = []
        for kw in kwargs:
            if kw not in default_dict:
                not_deflt.append(kw)
            else:
                default_dict[kw]=kwargs[kw]
        self.attribs = dict(default_dict)
        
        self.__categories = {}
        self.__weakgradeset = weakref.WeakSet()
        self.get_stat = self.get_weighted_stat
    
    def add_category(self,*categories):
        errList=[]
        for cat in categories:
            if type(cat) is Category:
                if cat.name in self:
                    errList.append(cat.name)
                    continue
                cat.parent=self
                self.__categories[cat.name]=cat
                self.__weakgradeset.add(cat)
        if errList:
            err = 'Attempt to add Categor(y/ies) named '
            err += list_to_str(errList)
            err+=' failed. Names already in Gradebook.'
            raise NameError,err
    
    def remove_category(self,cat):
        """cat may be a Category or a Category name"""
        if isinstance(cat,Category):
            cat = cat.name
        if cat.name in self.__categories:
            del self.__categories[cat.name]
            return True
        else:
            warnings.warn('Category \'{}\' is not in Gradebook.'.format(cat.name))
            return False
    
    def __contains__(self,x):
        for i in self.__weakgradeset:
            if (x == i.name) or (x is i) or (x == i):
                return True
        return False
    
    def __getitem__(self,x):
        ret = self.get_category(x)
        if not ret:
            ret = self.get_grade(x)
        if not ret:
            raise KeyError, 'Name \'{}\' not found in Gradebook.'.format(x)
        return ret
    
    def get_category(self,name):
        if name in self.__categories:
            return self.__categories[name]
        return None
    
    def get_grade(self,name):
        for cat in self.__categories.values():
            if name in cat.grades:
                return cat.grades[name]
        return None
    
    def add_grade(self,cat_name,grade_arg):
        if cat_name not in self.__categories:
            raise ValueError,'Category \'{}\' not in Gradebook.'.format(cat_name)
        if isinstance(grade_arg,Grade):
            if grade_arg in self:
                return False
            self.__categories[cat_name].grades.add_grade(grade_arg)
        else:
            if grade_arg in self:
                return False
            self.__categories[cat_name].grades.add_grade(Grade(grade_arg))
        return True
    
    def get_weighted_stat(self,stat):
        """Get information about Gradebook's grades.
        
        stat =      ( score | max[imum] | percent[age] )
        """
        if stat == 'score': statv=1
        elif stat.startswith('max'): statv=2
        elif stat.startswith('percent'): 
            statv=3
            stat='points'
        else:
            raise ValueError, 'Gradebook.get_weighted_stat passed unaccepted argument.'
        wpoints=0
        wmax=0
        for cat in self.__categories.values():
            p = cat.grades.get_stat('points',weighted=True,counted=True)
            if p:
                wpoints+=p
            m = cat.grades.get_stat('weights',counted=True)
            if m:
                wmax+=m
        if statv is 1:
            return wpoints
        if statv is 2:
            return wmax
        else:#percent
            if wmax:
                return 1.0*wpoints/wmax
            else:
                return None
    
    def identifier_select(self,**kwargs):
        retset=set()
        for cat in self.__categories:
            i = cat.grades.identifier_select(**kwargs)
            if i:
                retset |= i
        return retset
    
    def select(self,aslist=False,**kwargs):
        if not aslist and 'aslist' in kwargs:
            aslist = kwargs['aslist']
            del kwargs['aslist']
        retset=set()
        for cat in self.__categories.values():
            i = cat.grades.select(**kwargs)
            if i:
                retset |= i
        if aslist:
            return list(retset)
        return retset
    

def json_import(json_file,import_types=['Gradelist','Category','Grade'],inherit=False):
    """Import JSON file holding representations of grading data structures.
    
    Must be a list of grading classes, as seen below (not all parts needed).
    If 'inherit' is True, there must be a Gradebook defined in the file,
        and each Category will have its "parent" attribute as the name of the
        Gradebook. Each Grade will have its "parent" attribute as the name
        of a Category defined in the file.
       *ANY NON-CHILD NODES WILL NOT BE RETURNED.
       *Returns the Gradebook only.
    -
    SCHEMA:                                 REQUIRED (has #)
    {"grading":                                 #
        [                                       #
            ####Gradebook#####
            {                                   #
                "type": "Gradebook",            #
                "name": %%%%%%,                 #
                "user": %%%%%%,                 #
                "identifiers": {
                    %%%%%%: %%%%%%%,
                    ....
                }
            }                                   #
        ,
            ####Category####
            {                                   #
                "type": "Category",             #
                "name": %%%%%%%%,               #
                "parent": %%%%%%%,              #<--- For 'parent' to work, it must be a valid parent
                                                #        IN THE SAME FILE
                "attribs": {
                    "controls_weight":  %bool%,
                    "grade_weight":     %number%,
                    "controls_maximum": %bool%,
                    "grade_maximum":    %number%,
                    "cat_weight":       %number%,
                    "use_best_count":   %bool%,
                    "element_count":    %integer%
                }
            }                                   #
        ,
            ####Grade####
            {                                   #
                "type": "Grade",                #
                "name": %%%%%%%,                #
                "parent": %%%%%%%,              #<--- For 'parent' to work, it must be a valid parent
                                                #        IN THE SAME FILE
                "attribs": {
                    "score": %number%,
                    "maximum": %number%,
                    "weight": %number%,
                    "overrides": [%%%,%%%,...],
                    "identifiers": {
                        %%%%%%: %%%%%%,
                        ....
                    }
                }
            }                                   #
        ]
    }
    """
    try:
        import json
    except ImportError:
        warnings.warn('Failed to import json module. Cannot execute json_import')
        return
    if not hasattr(json_file,'read'):
        if not isinstance(json_file,basestring) or not os.path.exists(json_file):
            raise ValueError, 'Argument \'json_file\' is not readable, ' \
                    'and could not be validated as a file path.'
        else:
            json_file = open(json_file)
    
    if not isinstance(import_types,list):
        if isinstance(import_types,basestring) and import_types in \
                 ['Gradelist','Category','Grade']:
            import_types = [import_types]
        else:
            raise ValueError, 'import_types argument not supported, should'\
                    ' be list including one or more classes from grading'
    
    decoder = json.JSONDecoder()
    json_decoded = decoder.decode(json_file.read())
    
    grading_list = json_decoded.values()[0]
    
    ret_list = []
    if not inherit:
        for obj in grading_list:
            if not isinstance(obj,dict):
                raise TypeError, 'Unexpected type in grading array: \'{}\''.format(type(obj))
            if 'type' not in obj:
                raise KeyError, 'Could not find \'type\' key in structure.'
            typ = obj.get('type')
            if typ not in ['Gradelist','Category','Grade']:
                raise ValueError, 'type value "{}" is not an accepted value.'.format(typ)
            if typ not in import_types:
                continue
            
            if 'name' not in obj:
                raise KeyError, 'Could not find \'name\' key in structure.'
            name = obj.get('name')
            
            attribs = obj.get('attribs',{})
            if not isinstance(attribs,dict):
                raise ValueError, 'attribs of \'{}\' is not an object as expected.'.format(name)
            
            if typ == 'Gradebook':
                identifs = obj.get('identifiers',{})
                user = obj.get('user')
                if not isinstance(identifs,dict):
                    identifs = {}
                ret_list.append(Gradebook(name,user,identifiers=identifs))
            elif typ == 'Category':
                ret_list.append(Category(name,**attribs))
            elif typ == 'Grade':
                ret_list.append(Grade(name,**attribs))
        return ret_list
    #for inherit
    
    grbk = [x for x in grading_list if x.get('type','') == 'Gradebook']
    if not grbk:
        raise ValueError, 'json_import requires a Gradebook in the file for inherit-mode.'
    grbk = grbk[0]
    grbknm = grbk.pop('name')
    grbk = Gradebook(grbknm,grbk.get('user'),identifiers=grbk.get('identifiers',{}))
    cat_dict = {}
    for itm in grading_list:
        if itm.get('type','') == 'Category':
            if 'name' not in itm:
                raise ValueError, 'Category missing a name in JSON file.'
            attribs = itm.get('attribs',{})
            if 'parent' in itm and itm['parent'] == grbknm:
                pass
            else:
                dbg('Category \'{}\'s parent does not match Gradebook name')
                continue
            cat_dict[itm['name']]=Category(itm['name'],**attribs)
    grbk.add_category(*cat_dict.values())
    
    for itm in grading_list:
        if itm.get('type','') == 'Grade':
            if 'name' not in itm:
                raise ValueError, 'Grade missing a name in JSON file.'
            attribs = itm.get('attribs',{})
            if 'parent' not in itm or itm['parent'] not in cat_dict:
                dbg('Grade parent does not match Category name')
                continue
            grbk.add_grade(itm['parent'],Grade(itm['name'],**attribs))
    return grbk



def json_export(json_file,gradebook):
    """Output a Gradebook to the file json_file
    
    json_file can be a writeable file-like object, or a filepath.
    WILL overwrite file!
    """
    
    try:
        import json
    except ImportError:
        warnings.warn('Failed to import json module. Cannot execute json_export')
        return
    if not hasattr(json_file,'write'):
        if not isinstance(json_file,basestring) or not \
                os.path.exists(os.path.dirname(os.path.abspath(json_file))):
            raise ValueError, 'Argument \'json_file\' is not readable, ' \
                    'and could not be validated as a file path.'
        else:
            json_file = open(json_file,'w+')
    
    if not isinstance(gradebook,Gradebook):
        raise TypeError, 'gradebook argument must be a Gradebook objcet.'
    
    cat_dict = dict(gradebook._Gradebook__categories)
    all_items = []
    for cat_name in cat_dict:
        gr_leest = cat_dict[cat_name].grades.select(docopy=True,aslist=True)
        for i in gr_leest:
            x = {}
            if not isinstance(i,Grade):
                continue
            x['type']='Grade'
            x['name']=i.name
            if i.parent is not None:
                if i.parent.name == cat_name or i.parent.name in cat_dict:
                    x['parent'] = i.parent.name
                else:
                    x['parent'] = None
            attribs = {}
            attribs['score'] = i.score
            attribs['maximum'] = i.maximum
            attribs['weight'] = i.weight
            attribs['extra_credit'] = i.extra_credit
            if i.overrides:
                attribs['overrides'] = list(i.overrides)
                for ovrrd in i.overrides:
                    if not isinstance(overrd,basestring):
                        attribs['overrides'].remove(overrd)
            if i.timestamp and isinstance(i.timestamp,datetime.datetime):
                tmstmp = calendar.timegm(i.timestamp.utctimetuple())
                attribs['timestamp'] = tmstmp
            if i.identifiers:
                attribs['identifiers'] = dict(i.identifiers)
            
            x['attribs'] = attribs
            all_items.append(x)
        catt = {'type':'Category','name':cat_name}
        if cat_dict[cat_name].parent is not None:
            catt['parent'] = cat_dict[cat_name].parent.name
        else:
            catt['parent'] = None
        catt['attribs'] = dict(cat_dict[cat_name]._Category__attribs)
        all_items.append(catt)
    
    grbk = {'type':'Gradebook','name':gradebook.name,'user':gradebook.user}
    all_items.append(grbk)
    enc_me = {"grading": all_items}
    
    encoder = json.JSONEncoder(indent=4,separators=(', ',': '))
    enc = encoder.encode(enc_me)
    
    json_file.write(enc)
    json_file.close()
